from __future__ import annotations

import asyncio
import contextlib
import logging
import socket
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional, Set

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    DOMAIN,
    DEFAULT_SCAN_TIMEOUT,
    DISCOVERY_OPCODE,
    DISCOVERY_RESPONSE_OPCODE,
    CH_STATUS_RESP,
    RCU_TYPES_OPCODE,
    RCU_STATES_OPCODE,
)
from .protocol import build_packet, parse_smartcloud_packet

_LOGGER = logging.getLogger(__name__)


def _extract_cstr(data: bytes) -> str:
    """Extract 0-terminated string from bytes."""
    if not data:
        return ""
    try:
        end = data.index(0)
        data = data[:end]
    except ValueError:
        pass
    try:
        return data.decode("utf-8", errors="ignore").strip()
    except Exception:
        return ""


def _parse_0034(add: bytes) -> tuple[int, list[int]]:
    # add[0]=qty, add[1..]=values (0-100)
    if not add:
        return 0, []
    qty = add[0]
    vals = list(add[1 : 1 + qty]) if qty > 0 else []
    return qty, vals


def _parse_0005(add: bytes) -> tuple[int, Optional[int], list[int]]:
    # observed: [qty][kind][types...]
    if not add or len(add) < 2:
        return 0, None, []
    qty = add[0]
    kind = add[1]
    types = list(add[2 : 2 + qty]) if len(add) >= 2 + qty else list(add[2:])
    return qty, kind, types


@dataclass
class TisDeviceInfo:
    """Discovered device + last seen packets and parsed channel caches."""

    unique_id: str  # "{gw_ip}-{sub}-{dev}"
    gw_ip: str
    src_sub: int
    src_dev: int

    name: str = ""
    device_type: Optional[int] = None
    last_seen: float = 0.0
    opcodes_seen: Set[int] = field(default_factory=set)
    raw: dict = field(default_factory=dict)

    # --- RCU caches / channel data ---
    rcu_qty: Optional[int] = None
    rcu_kind: Optional[int] = None
    rcu_types: list[int] = field(default_factory=list)   # from 0x0005
    rcu_states: list[int] = field(default_factory=list)  # from 0x2025
    ch_levels: list[int] = field(default_factory=list)   # from 0x0034

    @property
    def src_str(self) -> str:
        return f"{self.src_sub}.{self.src_dev}"

    @property
    def device_type_hex(self) -> str:
        if self.device_type is None:
            return ""
        return f"0x{self.device_type:04X}"


@dataclass
class TisState:
    last_rx_ts: float | None = None
    discovered: Dict[str, TisDeviceInfo] = field(default_factory=dict)  # key=unique_id


class TisUdpClient:
    """UDP client that listens and updates internal state from SmartCloud packets."""

    def __init__(self, hass: HomeAssistant, host: str, port: int):
        self.hass = hass
        self.host = host
        self.port = port

        self._sock: Optional[socket.socket] = None
        self._task: Optional[asyncio.Task] = None
        self.state = TisState()
        self._listeners: list[Callable[[], None]] = []

    @callback
    def add_listener(self, cb: Callable[[], None]) -> Callable[[], None]:
        """Register a callback called whenever state changes."""
        self._listeners.append(cb)

        @callback
        def _remove() -> None:
            if cb in self._listeners:
                self._listeners.remove(cb)

        return _remove

    def _notify(self) -> None:
        for cb in list(self._listeners):
            try:
                cb()
            except Exception:
                _LOGGER.exception("Listener error")

    async def async_start(self) -> None:
        if self._sock:
            return

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.setblocking(False)

        sock.bind((self.host, self.port))

        self._sock = sock
        self._task = asyncio.create_task(self._recv_loop())

    async def async_stop(self) -> None:
        if self._task:
            self._task.cancel()
            with contextlib.suppress(Exception):
                await self._task
            self._task = None

        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None

    async def discover(self, timeout: float = DEFAULT_SCAN_TIMEOUT) -> Dict[str, TisDeviceInfo]:
        """Send broadcast discovery and wait for responses."""
        if not self._sock:
            await self.async_start()
        assert self._sock is not None

        loop = asyncio.get_running_loop()
        source_ip = self.host if self.host and self.host != "0.0.0.0" else "0.0.0.0"

        pkt_list = build_packet(
            operation_code=[(DISCOVERY_OPCODE >> 8) & 0xFF, DISCOVERY_OPCODE & 0xFF],
            ip_address=source_ip,
            device_id=[0xFF, 0xFF],
            source_device_id=[0x00, 0x00],
            additional_packets=[],
        )
        pkt = bytes(pkt_list)

        await loop.sock_sendto(self._sock, pkt, ("255.255.255.255", self.port))

        end = time.time() + float(timeout)
        while time.time() < end:
            await asyncio.sleep(0.05)

        return dict(self.state.discovered)

    async def _recv_loop(self) -> None:
        assert self._sock is not None
        loop = asyncio.get_running_loop()

        while True:
            try:
                data, addr = await loop.sock_recvfrom(self._sock, 4096)
            except asyncio.CancelledError:
                return
            except Exception:
                await asyncio.sleep(0.1)
                continue

            self.state.last_rx_ts = time.time()

            parsed = parse_smartcloud_packet(data)
            if not parsed or not parsed.get("valid", False):
                continue

            gw_ip = parsed.get("ip_address") or addr[0]
            src = parsed.get("source_device") or (0, 0)
            src_sub, src_dev = int(src[0]), int(src[1])
            dev_type = parsed.get("device_type")
            op_code = parsed.get("operation_code")
            add = parsed.get("additional_data", b"")

            unique_id = f"{gw_ip}-{src_sub}-{src_dev}"
            info = self.state.discovered.get(unique_id)
            if info is None:
                info = TisDeviceInfo(
                    unique_id=unique_id,
                    gw_ip=str(gw_ip),
                    src_sub=src_sub,
                    src_dev=src_dev,
                )

            info.last_seen = time.time()
            info.raw = parsed
            if isinstance(dev_type, int):
                info.device_type = dev_type
            if isinstance(op_code, int):
                info.opcodes_seen.add(op_code)

            # Discovery response -> device name
            if op_code == DISCOVERY_RESPONSE_OPCODE:
                name = _extract_cstr(add)
                if name:
                    info.name = name

            # RCU channel types
            if op_code == RCU_TYPES_OPCODE:
                qty, kind, types = _parse_0005(add)
                if qty:
                    info.rcu_qty = qty
                    info.rcu_kind = kind
                    info.rcu_types = types

            # RCU states (raw bytes list)
            if op_code == RCU_STATES_OPCODE:
                info.rcu_states = list(add)

            # Channel status response (levels)
            if op_code == CH_STATUS_RESP:
                qty, vals = _parse_0034(add)
                if qty:
                    info.ch_levels = vals

            self.state.discovered[unique_id] = info
            self._notify()


class TisCoordinator(DataUpdateCoordinator[TisState]):
    """Coordinator that mirrors TisUdpClient state and notifies entities."""

    def __init__(self, hass: HomeAssistant, client: TisUdpClient):
        super().__init__(
            hass=hass,
            logger=_LOGGER,
            name=f"{DOMAIN}_coordinator",
            update_interval=None,
        )
        self.client = client
        self.data = client.state

        self._unsub = self.client.add_listener(self._on_client_update)

    @callback
    def _on_client_update(self) -> None:
        self.async_set_updated_data(self.client.state)

    async def async_start(self) -> None:
        await self.client.async_start()

    async def async_discover(self) -> Dict[str, TisDeviceInfo]:
        await self.client.discover()
        self.async_set_updated_data(self.client.state)
        return dict(self.client.state.discovered)

    async def async_stop(self) -> None:
        if self._unsub:
            self._unsub()
            self._unsub = None
        await self.client.async_stop()

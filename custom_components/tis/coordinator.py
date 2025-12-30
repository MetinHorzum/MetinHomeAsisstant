from __future__ import annotations

import asyncio
import logging
import socket
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Set

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    DOMAIN,
    DEFAULT_SCAN_TIMEOUT,
    DISCOVERY_OPCODE,
    DISCOVERY_RESPONSE_OPCODE,
    DEVICE_TYPES,
)
from .protocol import build_packet, parse_smartcloud_packet

_LOGGER = logging.getLogger(__name__)


def _extract_cstr(data: bytes) -> str:
    """0-terminated (C string) decode."""
    if not data:
        return ""
    nul = data.find(b"\x00")
    if nul != -1:
        data = data[:nul]
    try:
        return data.decode("utf-8", errors="ignore").strip()
    except Exception:
        return ""


@dataclass
class TisDeviceInfo:
    """Discovery list item (TIS_UDP_Tester list view equivalent)."""

    unique_id: str  # "{gw_ip}-{sub}-{dev}"
    gw_ip: str
    src_sub: int
    src_dev: int

    name: str = ""
    device_type: Optional[int] = None
    last_seen: float = 0.0
    opcodes_seen: Set[int] = field(default_factory=set)

    @property
    def src_str(self) -> str:
        return f"{self.src_sub}.{self.src_dev}"

    @property
    def device_type_hex(self) -> str:
        if self.device_type is None:
            return ""
        return f"0x{self.device_type:04X}"

    @property
    def device_model(self) -> str:
        if self.device_type is None:
            return ""
        return DEVICE_TYPES.get(self.device_type, self.device_type_hex)


@dataclass
class TisState:
    last_rx_ts: float | None = None
    discovered: Dict[str, TisDeviceInfo] = field(default_factory=dict)  # key=unique_id


class TisUdpClient:
    """UDP discovery + receive loop for TIS SmartCloud packets."""

    def __init__(self, hass: HomeAssistant, host: str, port: int):
        self.hass = hass
        self.host = host
        self.port = port

        self._sock: Optional[socket.socket] = None
        self._task: Optional[asyncio.Task] = None
        self.state = TisState()

    async def async_start(self) -> None:
        if self._sock:
            return

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.setblocking(False)

        # Listen on the same UDP port as devices send replies to (6000 by default)
        sock.bind(("", self.port))

        self._sock = sock
        self._task = asyncio.create_task(self._recv_loop())

    async def async_stop(self) -> None:
        if self._task:
            self._task.cancel()
            self._task = None
        if self._sock:
            try:
                self._sock.close()
            finally:
                self._sock = None

    def _get_local_ip_for_gateway(self) -> str:
        """Best-effort local IP detection for the LAN."""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect((self.host, self.port))
            return s.getsockname()[0]
        except Exception:
            return "192.168.1.100"
        finally:
            s.close()

    async def discover(self, timeout: float = DEFAULT_SCAN_TIMEOUT) -> Dict[str, TisDeviceInfo]:
        """Broadcast discovery (0x000E) and collect responses (0x000F)."""
        await self.async_start()
        assert self._sock is not None
        loop = asyncio.get_running_loop()

        source_ip = self._get_local_ip_for_gateway()

        pkt_list = build_packet(
            operation_code=[(DISCOVERY_OPCODE >> 8) & 0xFF, DISCOVERY_OPCODE & 0xFF],
            ip_address=source_ip,
            device_id=[0xFF, 0xFF],
            source_device_id=[0x00, 0x00],
            additional_packets=[],
        )
        pkt = bytes(pkt_list)

        # Send to broadcast
        await loop.sock_sendto(self._sock, pkt, ("255.255.255.255", self.port))

        # Wait for responses to populate state.discovered via recv_loop
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
            if not parsed.get("valid"):
                continue
            if not parsed.get("crc_valid", True):
                continue

            gw_ip = addr[0]
            op_code = parsed.get("op_code")
            src = parsed.get("source_device") or [None, None]
            src_sub, src_dev = src[0], src[1]
            dev_type = parsed.get("device_type")

            # discovery row key: GW IP + SRC subnet/dev
            if src_sub is None or src_dev is None:
                continue

            unique_id = f"{gw_ip}-{int(src_sub)}-{int(src_dev)}"

            info = self.state.discovered.get(unique_id)
            if info is None:
                info = TisDeviceInfo(
                    unique_id=unique_id,
                    gw_ip=gw_ip,
                    src_sub=int(src_sub),
                    src_dev=int(src_dev),
                )

            info.last_seen = time.time()
            if isinstance(dev_type, int):
                info.device_type = dev_type
            if isinstance(op_code, int):
                info.opcodes_seen.add(op_code)

            # 0x000F -> name in additional_data
            if op_code == DISCOVERY_RESPONSE_OPCODE:
                name = _extract_cstr(parsed.get("additional_data", b""))
                if name:
                    info.name = name

            self.state.discovered[unique_id] = info


class TisCoordinator(DataUpdateCoordinator[TisState]):
    def __init__(self, hass: HomeAssistant, client: TisUdpClient):
        super().__init__(
            hass=hass,
            logger=_LOGGER,
            name=f"{DOMAIN}_coordinator",
            update_interval=None,  # manual refresh only
        )
        self.client = client
        self.data = client.state

    async def async_start(self) -> None:
        await self.client.async_start()

    async def async_discover(self) -> Dict[str, TisDeviceInfo]:
        await self.client.discover()
        self.async_set_updated_data(self.client.state)
        return dict(self.client.state.discovered)

from __future__ import annotations

import asyncio
import logging
import socket
import time
from datetime import timedelta
from dataclasses import dataclass, field
from typing import Dict, Optional, Set, List

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    DOMAIN,
    DEFAULT_SCAN_TIMEOUT,
    DISCOVERY_OPCODE,
    DISCOVERY_RESPONSE_OPCODE,
    DEVICE_TYPES,
    RCU_DEVICE_TYPE,
    RCU_TYPES_OPCODE,
    RCU_STATES_QUERY_OPCODE,
    RCU_STATES_RESPONSE_OPCODE,
    RCU_CH_NAME_QUERY_OPCODE,
    RCU_CH_NAME_RESPONSE_OPCODE,
    RCU_DI_QUERY_OPCODE,
    RCU_DI_RESPONSE_OPCODE,
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

    # ---- RCU caches (filled opportunistically from UDP traffic) ----
    rcu_types: List[int] = field(default_factory=list)     # per-channel type byte
    rcu_states: List[int] = field(default_factory=list)    # per-channel raw state byte
    rcu_names: Dict[int, str] = field(default_factory=dict)  # ch -> name

    # Digital inputs ("Mechanical switch" page) - decoded as bitfield
    rcu_di_bits: List[bool] = field(default_factory=list)  # di1..diN

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

    async def _send(self, op_code: int, *, target_sub: int, target_dev: int, additional: list[int] | None = None) -> None:
        """Send a SmartCloud packet as broadcast.

        We broadcast because the official tools do so (and it keeps the gateway routing consistent).
        """
        await self.async_start()
        assert self._sock is not None
        loop = asyncio.get_running_loop()

        source_ip = self._get_local_ip_for_gateway()
        pkt_list = build_packet(
            operation_code=[(op_code >> 8) & 0xFF, op_code & 0xFF],
            ip_address=source_ip,
            device_id=[target_sub & 0xFF, target_dev & 0xFF],
            source_device_id=[0x01, 0xFE],
            additional_packets=list(additional or []),
        )
        await loop.sock_sendto(self._sock, bytes(pkt_list), ("255.255.255.255", self.port))

    async def poll_rcu(self, info: TisDeviceInfo) -> None:
        """Best-effort polling for an RCU device.

        - types (0x0005)
        - states (0x2024 -> 0x2025)
        - names (0xF00E -> 0xF00F) lazily
        - digital inputs (0xD218 -> 0xD219) best-effort
        """
        # Types + states are safe to call periodically
        await self._send(RCU_TYPES_OPCODE, target_sub=info.src_sub, target_dev=info.src_dev)
        await self._send(RCU_STATES_QUERY_OPCODE, target_sub=info.src_sub, target_dev=info.src_dev)

        # Digital inputs (mechanical switch page). The capture shows an "index" byte (0x0A) and a selector 0/1.
        # We mirror that pattern as best-effort; if it doesn't match your setup, we'll still learn from incoming traffic.
        await self._send(RCU_DI_QUERY_OPCODE, target_sub=info.src_sub, target_dev=info.src_dev, additional=[0x0A, 0x00])
        await self._send(RCU_DI_QUERY_OPCODE, target_sub=info.src_sub, target_dev=info.src_dev, additional=[0x0A, 0x01])

        # Lazily fetch missing channel names (a few per poll to avoid flooding)
        qty = len(info.rcu_types) or len(info.rcu_states)
        if qty:
            missing = [ch for ch in range(1, qty + 1) if ch not in info.rcu_names]
            for ch in missing[:3]:
                await self._send(RCU_CH_NAME_QUERY_OPCODE, target_sub=info.src_sub, target_dev=info.src_dev, additional=[ch & 0xFF])

        # (no further actions)

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

            # ---- RCU specifics ----
            if info.device_type == RCU_DEVICE_TYPE:
                add = parsed.get("additional_data", b"") or b""

                # 0x0005 types: observed as [qty][kind][types..] in tool; accept both forms.
                if op_code == RCU_TYPES_OPCODE and add:
                    if len(add) >= 2 and add[0] <= 64:
                        qty = add[0]
                        # kind = add[1] (unused for now)
                        types = list(add[2:2 + qty]) if len(add) >= 2 + qty else list(add[2:])
                    else:
                        # fallback: treat whole payload as types
                        types = list(add)
                    if types:
                        info.rcu_types = types

                # 0x2025 states: payload seems to be per-channel bytes
                if op_code == RCU_STATES_RESPONSE_OPCODE and add:
                    info.rcu_states = list(add)

                # 0xF00F name response: assume [ch][cstr]
                if op_code == RCU_CH_NAME_RESPONSE_OPCODE and add:
                    ch = int(add[0])
                    nm = _extract_cstr(add[1:])
                    if ch > 0 and nm:
                        info.rcu_names[ch] = nm

                # 0xD219 digital inputs response: treat remaining bytes as a bitfield (order may need tweaking)
                if op_code == RCU_DI_RESPONSE_OPCODE and add and len(add) >= 4:
                    # capture shows prefix like: F8 0A <sel> ... <bitfield>
                    bit_bytes = add[3:]
                    bit_int = int.from_bytes(bit_bytes, "big", signed=False)
                    bits: list[bool] = []
                    for i in range(len(bit_bytes) * 8):
                        # MSB-first (best effort); if inverted, we can flip later once we compare with your labels
                        mask = 1 << (len(bit_bytes) * 8 - 1 - i)
                        bits.append(bool(bit_int & mask))
                    info.rcu_di_bits = bits

            self.state.discovered[unique_id] = info


class TisCoordinator(DataUpdateCoordinator[TisState]):
    def __init__(self, hass: HomeAssistant, client: TisUdpClient):
        super().__init__(
            hass=hass,
            logger=_LOGGER,
            name=f"{DOMAIN}_coordinator",
            update_interval=timedelta(seconds=5),
        )
        self.client = client
        self.data = client.state

    async def _async_update_data(self) -> TisState:
        # Poll only devices we already discovered; we rely on the UDP receive loop to fill caches.
        for dev in list(self.client.state.discovered.values()):
            if dev.device_type == RCU_DEVICE_TYPE:
                try:
                    await self.client.poll_rcu(dev)
                except Exception:
                    # Keep coordinator healthy even if device/gateway rejects a packet.
                    continue
        return self.client.state

    async def async_start(self) -> None:
        await self.client.async_start()

    async def async_discover(self) -> Dict[str, TisDeviceInfo]:
        await self.client.discover()
        self.async_set_updated_data(self.client.state)
        return dict(self.client.state.discovered)

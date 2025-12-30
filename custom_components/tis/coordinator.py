from __future__ import annotations

import asyncio
import logging
import socket
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Set

from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import dispatcher_send
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    DOMAIN,
    DEFAULT_SCAN_TIMEOUT,
    DISCOVERY_OPCODE,
    DISCOVERY_RESPONSE_OPCODE,
    SIGNAL_TIS_UPDATE,
    DEVICE_TYPES,
)
from .protocol import build_packet, parse_smartcloud_packet

_LOGGER = logging.getLogger(__name__)


def _extract_cstr(data: bytes) -> str:
    """0-terminated (C string) decode from additional_data."""
    if not data:
        return ""
    nul = data.find(b"\x00")
    if nul != -1:
        data = data[:nul]
    try:
        return data.decode("utf-8", errors="ignore").strip()
    except Exception:
        return ""



def _parse_0005(add: bytes) -> tuple[int, list[int]]:
    """RCU channel types (0x0005): [qty][kind][types...]"""
    if not add:
        return 0, []
    qty = add[0]
    if qty <= 0:
        return 0, []
    types = list(add[2:2 + qty]) if len(add) >= 2 + qty else list(add[2:])
    return qty, types


def _parse_2025(add: bytes) -> list[int]:
    """RCU channel states list (0x2025)."""
    return list(add) if add else []



@dataclass
class TisDeviceInfo:
    """Discovery satırı: GW IP + Source Subnet/Device + type + name vb."""
    unique_id: str  # "{gw_ip}-{sub}-{dev}"
    gw_ip: str
    src_sub: int
    src_dev: int

    name: str = ""
    device_type: Optional[int] = None
    last_seen: float = 0.0
    opcodes_seen: Set[int] = field(default_factory=set)
    raw: dict = field(default_factory=dict)

    # Parsed channel metadata/state for RCU-like devices
    channel_count: int | None = None
    channel_types: list[int] = field(default_factory=list)   # 0=unused,1=input,2=output
    channel_states: list[int] = field(default_factory=list)  # 0/1 values from 0x2025
    channel_levels: list[int] = field(default_factory=list)  # 0-100 values from 0x0034 (optional)

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

        # Listen on the UDP port (6000 by default) for device replies
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

    
    async def send_rcu_types(self, device: "TisDeviceInfo") -> None:
        """Request RCU channel types (op 0x0005)."""
        await self._send_simple_opcode(device, 0x0005)

    async def send_rcu_states(self, device: "TisDeviceInfo") -> None:
        """Request RCU channel states (op 0x2025)."""
        await self._send_simple_opcode(device, 0x2025)

    async def _send_simple_opcode(self, device: "TisDeviceInfo", op: int) -> None:
        """Send an opcode with empty additional payload to a device."""
        await self.async_start()
        assert self._sock is not None
        loop = asyncio.get_running_loop()

        source_ip = self._get_local_ip_for_gateway()
        dev_type = device.device_type if device.device_type is not None else 0xFFFE

        pkt_list = build_packet(
            operation_code=[(op >> 8) & 0xFF, op & 0xFF],
            ip_address=source_ip,
            device_id=[device.src_sub & 0xFF, device.src_dev & 0xFF],
            source_device_id=[0x00, 0x00],
            device_type=[(int(dev_type) >> 8) & 0xFF, int(dev_type) & 0xFF],
            additional_packets=[],
        )
        await loop.sock_sendto(self._sock, bytes(pkt_list), (device.gw_ip, self.port))
async def send_set_channel(
        self,
        device: TisDeviceInfo,
        channel: int,
        value: int,
        ramp_seconds: int = 0,
    ) -> None:
        """Set a single channel value on a device (op 0x0031).

        channel: 1-based
        value: 0-100 (relay için 0/100)
        """
        await self.async_start()
        assert self._sock is not None
        loop = asyncio.get_running_loop()

        source_ip = self._get_local_ip_for_gateway()
        op = 0x0031

        payload = [
            int(channel) & 0xFF,
            int(value) & 0xFF,
            (int(ramp_seconds) >> 8) & 0xFF,
            int(ramp_seconds) & 0xFF,
        ]

        dev_type = device.device_type if device.device_type is not None else 0xFFFE

        pkt_list = build_packet(
            operation_code=[(op >> 8) & 0xFF, op & 0xFF],
            ip_address=source_ip,
            device_id=[device.src_sub & 0xFF, device.src_dev & 0xFF],
            source_device_id=[0x00, 0x00],
            device_type=[(int(dev_type) >> 8) & 0xFF, int(dev_type) & 0xFF],
            additional_packets=payload,
        )

        await loop.sock_sendto(self._sock, bytes(pkt_list), (device.gw_ip, self.port))

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
            info.raw = parsed
            if isinstance(dev_type, int):
                info.device_type = dev_type
            if isinstance(op_code, int):
                info.opcodes_seen.add(op_code)

            # 0x000F -> name in additional_data
            if op_code == DISCOVERY_RESPONSE_OPCODE:
                name = _extract_cstr(parsed.get("additional_data", b""))
                if name:
                    info.name = name

            # 0x0005 -> channel types (RCU)
            if op_code == 0x0005:
                qty, types = _parse_0005(parsed.get("additional_data", b""))
                if qty:
                    info.channel_count = qty
                if types:
                    info.channel_types = types

            # 0x2025 -> channel states list (RCU)
            if op_code == 0x2025:
                states = _parse_2025(parsed.get("additional_data", b""))
                if states:
                    info.channel_states = states

            self.state.discovered[unique_id] = info
            dispatcher_send(self.hass, SIGNAL_TIS_UPDATE,
    DEVICE_TYPES, unique_id)


class TisCoordinator(DataUpdateCoordinator[TisState]):
    def __init__(self, hass: HomeAssistant, client: TisUdpClient):
        super().__init__(
            hass=hass,
            logger=_LOGGER,
            name=f"{DOMAIN}_coordinator",
            update_interval=None,
        )
        self.client = client
        self.data = client.state
        self._poll_task: asyncio.Task | None = None

    async def async_start(self) -> None:
        await self.client.async_start()
        if self._poll_task is None:
            self._poll_task = self.hass.async_create_task(self._poll_loop())

    async def async_discover(self) -> Dict[str, TisDeviceInfo]:
        await self.client.discover()
        self.async_set_updated_data(self.client.state)
        return dict(self.client.state.discovered)

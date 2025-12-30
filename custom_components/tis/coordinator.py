from __future__ import annotations

import asyncio
import logging
import socket
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Set, Tuple, List

from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import dispatcher_send
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    DOMAIN,
    DEFAULT_SCAN_TIMEOUT,
    DISCOVERY_OPCODE,
    DISCOVERY_RESPONSE_OPCODE,
    DEVICE_TYPES,
    SIGNAL_TIS_UPDATE,
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


def _parse_0005(add: bytes) -> Tuple[int, List[int]]:
    """RCU channel types (0x0005): [qty][kind][types...]"""
    if not add:
        return 0, []
    qty = add[0]
    if qty <= 0:
        return 0, []
    # add[1] seems "kind" in captures/tester; types start at index 2
    types = list(add[2:2 + qty]) if len(add) >= 2 + qty else list(add[2:])
    return qty, types


def _parse_2025(add: bytes) -> List[int]:
    """RCU channel states list (0x2025)."""
    return list(add) if add else []


@dataclass
class TisDeviceInfo:
    unique_id: str
    gw_ip: str
    src_sub: int
    src_dev: int
    device_type: Optional[int] = None
    name: str = ""
    last_seen: float = 0.0
    opcodes_seen: Set[int] = field(default_factory=set)
    raw: Dict = field(default_factory=dict)

    # RCU parsed state
    channel_count: Optional[int] = None
    channel_types: List[int] = field(default_factory=list)   # 0=unused, 1=output, 2=input (per tester)
    channel_states: List[int] = field(default_factory=list)  # raw state bytes from 0x2025
    channel_levels: List[int] = field(default_factory=list)  # reserved for 0x0034 if needed later


@dataclass
class TisClientState:
    discovered: Dict[str, TisDeviceInfo] = field(default_factory=dict)
    last_packet_time: float = 0.0


class TisUdpClient:
    def __init__(self, hass: HomeAssistant, host: str, port: int) -> None:
        self.hass = hass
        self.host = host
        self.port = int(port)

        self.state = TisClientState()

        self._sock: Optional[socket.socket] = None
        self._recv_task: Optional[asyncio.Task] = None
        self._poll_task: Optional[asyncio.Task] = None
        self._running = False

    async def async_start(self) -> None:
        if self._running:
            return
        self._running = True

        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setblocking(False)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        try:
            # bind to listen on the configured port
            self._sock.bind(("", self.port))
        except OSError:
            # fallback to ephemeral port if bind fails
            self._sock.bind(("", 0))

        self._recv_task = asyncio.create_task(self._recv_loop(), name="tis_udp_recv")
        self._poll_task = asyncio.create_task(self._poll_loop(), name="tis_rcu_poll")

    async def async_stop(self) -> None:
        self._running = False
        if self._poll_task:
            self._poll_task.cancel()
            self._poll_task = None
        if self._recv_task:
            self._recv_task.cancel()
            self._recv_task = None
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None

    def _get_local_ip_for_gateway(self) -> List[int]:
        """Best-effort local IP bytes used in packet header."""
        # Use UDP connect trick to learn local IP for route
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect((self.host, self.port))
            ip = s.getsockname()[0]
            s.close()
        except Exception:
            ip = "0.0.0.0"
        parts = [int(p) & 0xFF for p in ip.split(".") if p.isdigit()]
        while len(parts) < 4:
            parts.append(0)
        return parts[:4]

    async def discover(self, timeout: float = DEFAULT_SCAN_TIMEOUT) -> Dict[str, TisDeviceInfo]:
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

        await loop.sock_sendto(self._sock, pkt, ("255.255.255.255", self.port))

        end = time.time() + float(timeout)
        while time.time() < end:
            await asyncio.sleep(0.05)

        return dict(self.state.discovered)

    async def _send_op(self, device: TisDeviceInfo, op_code: int, payload: List[int]) -> None:
        await self.async_start()
        assert self._sock is not None

        loop = asyncio.get_running_loop()
        source_ip = self._get_local_ip_for_gateway()

        dev_type = device.device_type if device.device_type is not None else 0xFFFE

        pkt_list = build_packet(
            operation_code=[(op_code >> 8) & 0xFF, op_code & 0xFF],
            ip_address=source_ip,
            device_id=[device.src_sub & 0xFF, device.src_dev & 0xFF],
            source_device_id=[0x00, 0x00],
            device_type=[(int(dev_type) >> 8) & 0xFF, int(dev_type) & 0xFF],
            additional_packets=[int(x) & 0xFF for x in payload],
        )
        await loop.sock_sendto(self._sock, bytes(pkt_list), (device.gw_ip, self.port))

    async def send_set_channel(
        self,
        device: TisDeviceInfo,
        channel: int,
        value: int,
        ramp_seconds: int = 0,
    ) -> None:
        """Set a single channel value on a device (op 0x0031)."""
        payload = [
            int(channel) & 0xFF,
            int(value) & 0xFF,
            (int(ramp_seconds) >> 8) & 0xFF,
            int(ramp_seconds) & 0xFF,
        ]
        await self._send_op(device, 0x0031, payload)

    async def request_rcu_types(self, device: TisDeviceInfo) -> None:
        await self._send_op(device, 0x0005, [])

    async def request_rcu_states(self, device: TisDeviceInfo) -> None:
        await self._send_op(device, 0x2025, [])

    async def _poll_loop(self) -> None:
        """Poll RCU devices for types (once) and states (periodically)."""
        while self._running:
            try:
                for dev in list(self.state.discovered.values()):
                    if dev.device_type is None:
                        continue
                    model = DEVICE_TYPES.get(dev.device_type, "")
                    if not model.startswith("RCU"):
                        continue

                    # types: request until we get them
                    if not dev.channel_types:
                        await self.request_rcu_types(dev)
                        await asyncio.sleep(0.05)

                    # states: poll every cycle
                    await self.request_rcu_states(dev)
                    await asyncio.sleep(0.05)

            except asyncio.CancelledError:
                return
            except Exception as err:
                _LOGGER.debug("RCU poll loop error: %s", err)

            await asyncio.sleep(10)

    async def _recv_loop(self) -> None:
        assert self._sock is not None
        loop = asyncio.get_running_loop()

        while self._running:
            try:
                data, (src_ip, _src_port) = await loop.sock_recvfrom(self._sock, 4096)
            except asyncio.CancelledError:
                return
            except Exception:
                await asyncio.sleep(0.05)
                continue

            self.state.last_packet_time = time.time()

            parsed = parse_smartcloud_packet(data)
            if not parsed or not parsed.get("valid"):
                continue

            gw_ip = str(src_ip)
            src_sub = int(parsed.get("source_device_subnet", 0))
            src_dev = int(parsed.get("source_device_id", 0))
            device_type = parsed.get("device_type")
            op_code = int(parsed.get("operation_code", 0))
            add = parsed.get("additional_data", b"")

            unique_id = f"{gw_ip}-{src_sub}-{src_dev}"

            info = self.state.discovered.get(unique_id)
            if info is None:
                info = TisDeviceInfo(
                    unique_id=unique_id,
                    gw_ip=gw_ip,
                    src_sub=src_sub,
                    src_dev=src_dev,
                )

            info.last_seen = time.time()
            info.opcodes_seen.add(op_code)
            info.raw = parsed
            if device_type is not None:
                info.device_type = int(device_type)

            if op_code == DISCOVERY_RESPONSE_OPCODE:
                name = _extract_cstr(add)
                if name:
                    info.name = name

            if op_code == 0x0005:
                qty, types = _parse_0005(add)
                if qty:
                    info.channel_count = qty
                if types:
                    info.channel_types = types

            if op_code == 0x2025:
                states = _parse_2025(add)
                if states:
                    info.channel_states = states

            self.state.discovered[unique_id] = info

            # Notify platforms (for dynamic entity creation / state refresh)
            dispatcher_send(self.hass, SIGNAL_TIS_UPDATE, unique_id)


class TisCoordinator(DataUpdateCoordinator[TisClientState]):
    def __init__(self, hass: HomeAssistant, client: TisUdpClient) -> None:
        super().__init__(
            hass=hass,
            logger=_LOGGER,
            name=f"{DOMAIN}_coordinator",
            update_interval=None,
        )
        self.client = client
        self.data = client.state

    async def async_start(self) -> None:
        await self.client.async_start()

    async def async_discover(self) -> Dict[str, TisDeviceInfo]:
        await self.client.discover()
        self.async_set_updated_data(self.client.state)
        return dict(self.client.state.discovered)

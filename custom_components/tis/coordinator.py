from __future__ import annotations

import asyncio
import logging
import socket
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Set, Tuple

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    DOMAIN,
    DEFAULT_SCAN_TIMEOUT,
    DISCOVERY_OPCODE,
    DISCOVERY_RESPONSE_OPCODE,
    DEVICE_TYPES,
    RCU_CH_TYPES_REQ,
    RCU_STATE_REQ,
    RCU_CH_NAMES_REQ,
    RCU_DI_REQ,
    RCU_STATE_RESP,
    RCU_DI_RESP,
    CH_SET_REQ,
)
from .protocol import build_packet, parse_smartcloud_packet

_LOGGER = logging.getLogger(__name__)


def _extract_cstr(data: bytes) -> str:
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
    discovered: Dict[str, TisDeviceInfo] = field(default_factory=dict)
    payloads: Dict[Tuple[int, int, int], bytes] = field(default_factory=dict)


class TisUdpClient:
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
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect((self.host, self.port))
            return s.getsockname()[0]
        except Exception:
            return "192.168.1.100"
        finally:
            s.close()

    async def _send(self, op_code: int, target: tuple[int, int], additional: list[int] | None = None) -> None:
        await self.async_start()
        assert self._sock is not None
        loop = asyncio.get_running_loop()

        source_ip = self._get_local_ip_for_gateway()
        op_bytes = [(op_code >> 8) & 0xFF, op_code & 0xFF]
        dev_id = [int(target[0]) & 0xFF, int(target[1]) & 0xFF]
        additional = additional or []

        pkt_list = build_packet(
            operation_code=op_bytes,
            ip_address=source_ip,
            device_id=dev_id,
            source_device_id=[0x01, 0xFE],
            device_type=[0xFF, 0xFE],
            additional_packets=additional,
        )
        pkt = bytes(pkt_list)

        await loop.sock_sendto(self._sock, pkt, ("255.255.255.255", self.port))

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

    async def rcu_refresh(self, sub: int, dev: int) -> None:
        await self._send(RCU_CH_TYPES_REQ, (sub, dev))
        await self._send(RCU_STATE_REQ, (sub, dev))
        await self._send(RCU_DI_REQ, (sub, dev), additional=[0x0A, 0x00])
        for ch in range(1, 25):
            await self._send(RCU_CH_NAMES_REQ, (sub, dev), additional=[ch & 0xFF])

    async def rcu_set_output(self, sub: int, dev: int, ch: int, on: bool) -> None:
        value = 100 if on else 0
        await self._send(CH_SET_REQ, (sub, dev), additional=[ch & 0xFF, value & 0xFF, 0x00, 0x00])

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
            add = parsed.get("additional_data", b"")

            if src_sub is None or src_dev is None or not isinstance(op_code, int):
                continue

            self.state.payloads[(int(src_sub), int(src_dev), int(op_code))] = bytes(add or b"")

            unique_id = f"{gw_ip}-{int(src_sub)}-{int(src_dev)}"

            info = self.state.discovered.get(unique_id)
            if info is None:
                info = TisDeviceInfo(unique_id=unique_id, gw_ip=gw_ip, src_sub=int(src_sub), src_dev=int(src_dev))

            info.last_seen = time.time()
            if isinstance(dev_type, int):
                info.device_type = dev_type
            info.opcodes_seen.add(int(op_code))

            if op_code == DISCOVERY_RESPONSE_OPCODE:
                name = _extract_cstr(add)
                if name:
                    info.name = name

            self.state.discovered[unique_id] = info


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

    async def async_start(self) -> None:
        await self.client.async_start()

    async def _async_update_data(self) -> TisState:
        await self.client.discover()
        for dev in list(self.client.state.discovered.values()):
            if dev.device_type == 0x802B:
                await self.client.rcu_refresh(dev.src_sub, dev.src_dev)
        return self.client.state

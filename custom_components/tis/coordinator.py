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
)
from .protocol import build_packet, parse_smartcloud_packet

_LOGGER = logging.getLogger(__name__)

@dataclass
class TisDeviceInfo:
    unique_id: str
    gw_ip: str
    src_sub: int
    src_dev: int
    name: str = ""
    device_type: Optional[int] = None
    last_seen: float = 0.0
    opcodes_seen: Set[int] = field(default_factory=set)
    raw: dict = field(default_factory=dict)

    @property
    def src_str(self) -> str:
        return f"{self.src_sub}.{self.src_dev}"

@dataclass
class TisState:
    last_rx_ts: float | None = None
    discovered: Dict[str, TisDeviceInfo] = field(default_factory=dict)

class TisUdpClient:
    def __init__(self, hass: HomeAssistant, host: str, port: int):
        self.hass = hass
        self.host = host
        self.port = port
        self._sock: Optional[socket.socket] = None
        self._task: Optional[asyncio.Task] = None
        self.state = TisState()

    async def async_start(self) -> None:
        if self._sock: return
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.setblocking(False)
        sock.bind(("", self.port))
        self._sock = sock
        self._task = asyncio.create_task(self._recv_loop())

    async def async_stop(self) -> None:
        if self._task: self._task.cancel()
        if self._sock: self._sock.close()

    async def async_send_command(self, target_sub: int, target_dev: int, opcode: int, payload: list):
        """Cihaza UDP paketi gönderir."""
        if not self._sock: return
        
        # Source ID olarak 1.254 (Standart PC/Server ID) kullanıyoruz
        pkt_list = build_packet(
            operation_code=[(opcode >> 8) & 0xFF, opcode & 0xFF],
            ip_address="0.0.0.0", # build_packet içinde otomatik çözülebilir veya dummy kalabilir
            source_device_id=[1, 254],
            device_id=[target_sub, target_dev],
            additional_packets=payload
        )
        loop = asyncio.get_running_loop()
        await loop.sock_sendto(self._sock, bytes(pkt_list), (self.host, self.port))

    async def discover(self, timeout: float = DEFAULT_SCAN_TIMEOUT):
        await self.async_start()
        # Discovery paketi gönderimi (0x000E)
        await self.async_send_command(0xFF, 0xFF, DISCOVERY_OPCODE, [])
        await asyncio.sleep(timeout)
        return self.state.discovered

    async def _recv_loop(self) -> None:
        loop = asyncio.get_running_loop()
        while True:
            try:
                data, addr = await loop.sock_recvfrom(self._sock, 4096)
                parsed = parse_smartcloud_packet(data)
                if not parsed.get("valid"): continue

                gw_ip = addr[0]
                src = parsed.get("source_device")
                unique_id = f"{gw_ip}-{src[0]}-{src[1]}"
                
                info = self.state.discovered.get(unique_id, TisDeviceInfo(unique_id, gw_ip, src[0], src[1]))
                info.last_seen = time.time()
                info.device_type = parsed.get("device_type")
                
                if parsed.get("op_code") == DISCOVERY_RESPONSE_OPCODE:
                    # C-String decode işlemi
                    name_bytes = parsed.get("additional_data", b"")
                    info.name = name_bytes.split(b'\x00')[0].decode('utf-8', 'ignore')

                self.state.discovered[unique_id] = info
                self.state.last_rx_ts = time.time()
            except Exception as e:
                _LOGGER.error("Recv loop error: %s", e)
                await asyncio.sleep(1)

class TisCoordinator(DataUpdateCoordinator[TisState]):
    def __init__(self, hass: HomeAssistant, client: TisUdpClient):
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=None)
        self.client = client
        self.data = client.state

    async def async_discover(self):
        await self.client.discover()
        self.async_set_updated_data(self.client.state)
from __future__ import annotations

import asyncio
import socket
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    DOMAIN,
    DEFAULT_SCAN_TIMEOUT,
    DISCOVERY_OPCODE,
    DISCOVERY_RESPONSE_OPCODE,
)

from .protocol import build_packet, parse_smartcloud_packet


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
    ip: str
    name: str = ""
    last_seen: float = 0.0
    raw: dict = field(default_factory=dict)


@dataclass
class TisState:
    last_rx_ts: float | None = None
    discovered: Dict[str, TisDeviceInfo] = field(default_factory=dict)


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

        # Wait for responses
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

            op_code = parsed.get("op_code")
            src_ip = addr[0]

            if op_code == DISCOVERY_RESPONSE_OPCODE:
                name = _extract_cstr(parsed.get("additional_data", b""))
                info = self.state.discovered.get(src_ip) or TisDeviceInfo(ip=src_ip)
                info.name = name or info.name
                info.last_seen = time.time()
                info.raw = parsed
                self.state.discovered[src_ip] = info
            else:
                # For future: handle telemetry opcodes here.
                pass


class TisCoordinator(DataUpdateCoordinator[TisState]):
    def __init__(self, hass: HomeAssistant, client: TisUdpClient):
        super().__init__(
            hass=hass,
            logger=None,
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

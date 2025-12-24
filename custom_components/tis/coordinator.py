from __future__ import annotations

import asyncio
import logging
import socket
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, DISCOVERY_OPCODE, DISCOVERY_RESPONSE_OPCODE
from .protocol import build_packet, parse_smartcloud_packet

_LOGGER = logging.getLogger(__name__)


@dataclass
class TisState:
    last_rx_ts: float | None = None
    discovered: Dict[str, Dict[str, Any]] = field(default_factory=dict)


class TisUdpClient:
    """UDP discovery + receive loop for TIS SmartCloud."""

    def __init__(self, hass: HomeAssistant, host: str, port: int, broadcast: str):
        self.hass = hass
        self.host = host
        self.port = port
        self.broadcast = broadcast

        self._sock: Optional[socket.socket] = None
        self._task: Optional[asyncio.Task] = None
        self.state = TisState()

    async def async_start(self) -> None:
        if self._sock:
            return

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setblocking(False)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        # listen on port 6000 like your sniffer
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

    def _local_ip_for_gateway(self) -> str:
        """Best-effort: pick the local IP that routes to the gateway."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect((self.host, self.port))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "0.0.0.0"

    async def discover(self, timeout: float = 2.0) -> Dict[str, Dict[str, Any]]:
        await self.async_start()
        assert self._sock is not None

        source_ip = self._local_ip_for_gateway()
        # IMPORTANT: build_packet expects *source* IP (your PC was 192.168.1.2 in the sniffer),
        # not the gateway IP. Using gateway IP causes devices to ignore the request.
        pkt_list = build_packet(
            operation_code=[(DISCOVERY_OPCODE >> 8) & 0xFF, DISCOVERY_OPCODE & 0xFF],
            ip_address=source_ip,
            device_id=[0xFF, 0xFF],  # broadcast target device
            source_device_id=[0x01, 0xFE],  # matches your GUI defaults
            device_type=[0xFF, 0xFE],
            additional_packets=[],
        )
        pkt = bytes(pkt_list)

        loop = asyncio.get_running_loop()
        await loop.sock_sendto(self._sock, pkt, (self.broadcast, self.port))

        end = time.time() + timeout
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
            except Exception as err:
                _LOGGER.debug("UDP recv error: %s", err)
                await asyncio.sleep(0.2)
                continue

            self.state.last_rx_ts = time.time()

            parsed = parse_smartcloud_packet(data)
            if not parsed or not parsed.get("valid"):
                continue

            op_code = parsed.get("op_code")
            if op_code != DISCOVERY_RESPONSE_OPCODE:
                continue

            src_ip = addr[0]
            src_dev = parsed.get("source_device") or [0, 0]
            tgt_dev = parsed.get("target_device") or [0, 0]
            # Discovery response'lar gateway IP'sinden gelebilir (hepsi aynı src_ip).
            # Bu yüzden anahtar olarak "source_device" çiftini kullanıyoruz.
            device_key = f"{src_dev[0]:02X}{src_dev[1]:02X}"
            info = {
                "src_ip": src_ip,
                "source_device": src_dev,
                "target_device": tgt_dev,
                "device_type": parsed.get("device_type"),
                "name": None,
                "op_code": op_code,
                "length": parsed.get("length"),
                "crc_valid": parsed.get("crc_valid"),
            }
            add = parsed.get("additional_data") or b""
            info["additional_hex"] = add.hex(" ")
            try:
                name = add.decode("ascii", errors="ignore").rstrip("\x00").strip()
                if name:
                    info["name"] = name
            except Exception:
                pass

            self.state.discovered[device_key] = info


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

    async def async_discover(self) -> Dict[str, Dict[str, Any]]:
        devices = await self.client.discover()
        self.async_set_updated_data(self.client.state)
        return devices

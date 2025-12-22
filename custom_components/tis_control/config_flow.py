"""Config flow for TIS Control integration."""
from __future__ import annotations

import asyncio
import socket
import logging
import voluptuous as vol
from typing import Any

from homeassistant import config_entries
from homeassistant.const import CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_PORT, default=4001): int,
})

STEP_DISCOVERY_DATA_SCHEMA = vol.Schema({
    vol.Required("network_range", default="192.168.1.0/24"): str,
    vol.Required("scan_timeout", default=3): int,
})


class TISConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for TIS Control."""

    VERSION = 1

    def __init__(self):
        """Initialize config flow."""
        self._discovered_devices = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            # Validate port
            port = user_input[CONF_PORT]
            if not isinstance(port, int) or not (1 <= port <= 65535):
                errors["base"] = "invalid_port"
            else:
                # Check if already configured
                await self.async_set_unique_id(f"tis_control_{port}")
                self._abort_if_unique_id_configured()
                
                # Store port for next step
                self._port = port
                
                # Go to discovery step
                return await self.async_step_discovery()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_discovery(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle network discovery step."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            network_range = user_input["network_range"]
            timeout = user_input["scan_timeout"]
            
            try:
                # Perform network discovery
                _LOGGER.info(f"🔍 TIS Cihaz Taraması Başlıyor: {network_range}")
                discovered = await self._discover_tis_devices(network_range, timeout)
                self._discovered_devices = discovered
                
                if discovered:
                    _LOGGER.info(f"✅ {len(discovered)} TIS cihazı bulundu!")
                    return await self.async_step_select_devices()
                else:
                    _LOGGER.warning("⚠️ TIS cihazı bulunamadı")
                    return await self.async_step_manual_setup()
                    
            except Exception as err:
                _LOGGER.error(f"Tarama hatası: {err}")
                errors["base"] = "scan_failed"

        return self.async_show_form(
            step_id="discovery",
            data_schema=STEP_DISCOVERY_DATA_SCHEMA,
            errors=errors,
            description_placeholders={
                "network_info": "Ağınızdaki TIS cihazları taranacak. Örnek: 192.168.1.0/24"
            }
        )

    async def async_step_select_devices(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle device selection step."""
        if user_input is not None:
            selected_devices = user_input.get("selected_devices", [])
            
            # Create entry with discovered devices
            return self.async_create_entry(
                title=f"TIS Control ({len(selected_devices)} cihaz)",
                data={
                    CONF_PORT: self._port,
                    "discovered_devices": selected_devices,
                    "discovery_enabled": True
                }
            )

        # Create device selection schema
        device_options = {}
        for device in self._discovered_devices:
            key = f"{device['ip']}:{device['port']}"
            name = f"{device.get('name', 'Bilinmeyen')} - {device['ip']}"
            device_options[key] = name

        if not device_options:
            return await self.async_step_manual_setup()

        schema = vol.Schema({
            vol.Required("selected_devices", default=list(device_options.keys())): 
                cv.multi_select(device_options)
        })

        return self.async_show_form(
            step_id="select_devices",
            data_schema=schema,
            description_placeholders={
                "device_count": str(len(self._discovered_devices))
            }
        )

    async def async_step_manual_setup(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle manual setup when no devices found."""
        if user_input is not None:
            return self.async_create_entry(
                title="TIS Control (Manuel Kurulum)",
                data={
                    CONF_PORT: self._port,
                    "discovered_devices": [],
                    "discovery_enabled": False
                }
            )

        return self.async_show_form(
            step_id="manual_setup",
            data_schema=vol.Schema({}),
            description_placeholders={
                "manual_info": "Otomatik tarama başarısız oldu. Manuel kurulum yapılacak."
            }
        )

    async def _discover_tis_devices(self, network_range: str, timeout: int) -> list:
        """Discover TIS devices on network."""
        discovered_devices = []
        
        try:
            # Parse network range (simplified for demo)
            if "/" in network_range:
                network_base = network_range.split("/")[0].rsplit(".", 1)[0]
            else:
                network_base = network_range.rsplit(".", 1)[0]
            
            # Scan common TIS ports
            tis_ports = [4001, 4002, 8080, 9090]
            
            tasks = []
            for i in range(1, 255):  # Scan IP range
                ip = f"{network_base}.{i}"
                for port in tis_ports:
                    tasks.append(self._check_tis_device(ip, port, timeout))
            
            # Execute all tasks with limited concurrency
            semaphore = asyncio.Semaphore(50)  # Limit concurrent connections
            
            async def sem_task(task):
                async with semaphore:
                    return await task
            
            results = await asyncio.gather(*[sem_task(task) for task in tasks], return_exceptions=True)
            
            for result in results:
                if isinstance(result, dict) and result.get("found"):
                    discovered_devices.append(result)
                    _LOGGER.info(f"TIS Cihazı bulundu: {result['ip']}:{result['port']}")
            
        except Exception as err:
            _LOGGER.error(f"Network discovery hatası: {err}")
        
        return discovered_devices

    async def _check_tis_device(self, ip: str, port: int, timeout: int) -> dict:
        """Check if device at IP:port is a TIS device."""
        try:
            # Try to connect to the device
            future = asyncio.open_connection(ip, port)
            reader, writer = await asyncio.wait_for(future, timeout=timeout)
            
            # Send TIS discovery packet (simplified)
            writer.write(b'\x55\xAA\x00\x01\x00\x00\x01')  # Sample TIS packet
            await writer.drain()
            
            # Try to read response
            try:
                response = await asyncio.wait_for(reader.read(100), timeout=timeout)
                writer.close()
                await writer.wait_closed()
                
                # Check if response looks like TIS protocol
                if response and len(response) >= 4:
                    return {
                        "found": True,
                        "ip": ip,
                        "port": port,
                        "name": f"TIS Device",
                        "response": response.hex()
                    }
            except asyncio.TimeoutError:
                pass
                
            writer.close()
            await writer.wait_closed()
            
        except (ConnectionRefusedError, asyncio.TimeoutError, OSError):
            pass
        except Exception as err:
            _LOGGER.debug(f"Check device error {ip}:{port}: {err}")
        
        return {"found": False}

    async def async_step_import(self, user_input: dict[str, Any]) -> FlowResult:
        """Handle import."""
        return await self.async_step_user(user_input)
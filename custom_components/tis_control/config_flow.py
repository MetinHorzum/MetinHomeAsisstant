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
    vol.Required(CONF_PORT, default=6000): int,
})

STEP_DISCOVERY_DATA_SCHEMA = vol.Schema({
    vol.Required("network_range", default="192.168.1.0/24"): str,
    vol.Required("scan_timeout", default=5): int,
    vol.Required("target_ip", default="192.168.1.200"): str,
    vol.Required("target_port", default=6000): int,
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
            target_ip = user_input["target_ip"]
            target_port = user_input["target_port"]
            
            try:
                _LOGGER.info(f"🔍 TIS Cihaz Taraması Başlıyor...")
                _LOGGER.info(f"📡 Hedef: {target_ip}:{target_port}")
                _LOGGER.info(f"🌐 Ağ Aralığı: {network_range}")
                
                # First test the specific target
                specific_result = await self._test_specific_device(target_ip, target_port, timeout)
                if specific_result:
                    self._discovered_devices.append(specific_result)
                    _LOGGER.info(f"✅ Hedef TIS cihazı bulundu: {target_ip}:{target_port}")
                
                # Then scan the network
                discovered = await self._discover_tis_devices(network_range, timeout, target_port)
                self._discovered_devices.extend(discovered)
                
                total_found = len(self._discovered_devices)
                if total_found > 0:
                    _LOGGER.info(f"🎯 Toplam {total_found} TIS cihazı bulundu!")
                    return await self.async_step_select_devices()
                else:
                    _LOGGER.warning("⚠️ Hiç TIS cihazı bulunamadı")
                    _LOGGER.info(f"💡 Manuel test: telnet {target_ip} {target_port}")
                    return await self.async_step_manual_setup()
                    
            except Exception as err:
                _LOGGER.error(f"Tarama hatası: {err}")
                errors["base"] = "scan_failed"

        return self.async_show_form(
            step_id="discovery",
            data_schema=STEP_DISCOVERY_DATA_SCHEMA,
            errors=errors,
            description_placeholders={
                "network_info": "Gerçek TIS cihazlarınızı bulalım!"
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
                title=f"TIS Control ({len(selected_devices)} gerçek cihaz)",
                data={
                    CONF_PORT: self._port,
                    "discovered_devices": selected_devices,
                    "discovery_enabled": True,
                    "real_devices": True
                }
            )

        # Create device selection schema
        device_options = {}
        for device in self._discovered_devices:
            key = f"{device['ip']}:{device['port']}"
            name = f"TIS Cihazı - {device['ip']}:{device['port']}"
            if device.get('response'):
                name += f" (Yanıt: {device['response'][:20]}...)"
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
                title="TIS Control (Test Modu)",
                data={
                    CONF_PORT: self._port,
                    "discovered_devices": [],
                    "discovery_enabled": False,
                    "real_devices": False
                }
            )

        return self.async_show_form(
            step_id="manual_setup",
            data_schema=vol.Schema({}),
            description_placeholders={
                "manual_info": "Otomatik tarama başarısız. Test modunda devam edilecek."
            }
        )

    async def _test_specific_device(self, ip: str, port: int, timeout: int) -> dict | None:
        """Test specific TIS device."""
        _LOGGER.info(f"🎯 Hedef cihaz test ediliyor: {ip}:{port}")
        
        try:
            # Simple socket connection test
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, port))
            sock.close()
            
            if result == 0:
                _LOGGER.info(f"✅ Bağlantı başarılı: {ip}:{port}")
                
                # Try to get more info with asyncio
                try:
                    reader, writer = await asyncio.wait_for(
                        asyncio.open_connection(ip, port), 
                        timeout=timeout
                    )
                    
                    # Send TIS discovery packet
                    tis_packet = bytes([0x55, 0xAA, 0x00, 0x01, 0x00, 0x00, 0x01])
                    writer.write(tis_packet)
                    await writer.drain()
                    
                    # Try to read response
                    try:
                        response = await asyncio.wait_for(reader.read(100), timeout=2)
                        writer.close()
                        await writer.wait_closed()
                        
                        _LOGGER.info(f"📦 TIS yanıtı alındı: {response.hex()}")
                        return {
                            "ip": ip,
                            "port": port,
                            "name": f"TIS Device {ip}",
                            "response": response.hex(),
                            "found": True
                        }
                    except asyncio.TimeoutError:
                        _LOGGER.info(f"⏰ TIS yanıt timeout: {ip}:{port}")
                        writer.close()
                        await writer.wait_closed()
                        
                        # Even without response, if connection works, it might be TIS
                        return {
                            "ip": ip,
                            "port": port,
                            "name": f"TIS Device {ip}",
                            "response": "no_response_but_connected",
                            "found": True
                        }
                        
                except Exception as e:
                    _LOGGER.debug(f"Asyncio bağlantı hatası {ip}:{port}: {e}")
                    # Fallback: if socket connection worked, assume it's TIS
                    return {
                        "ip": ip,
                        "port": port,
                        "name": f"TIS Device {ip}",
                        "response": "socket_connection_ok",
                        "found": True
                    }
            else:
                _LOGGER.warning(f"❌ Bağlantı başarısız: {ip}:{port} (hata kodu: {result})")
                
        except Exception as err:
            _LOGGER.debug(f"Cihaz test hatası {ip}:{port}: {err}")
        
        return None

    async def _discover_tis_devices(self, network_range: str, timeout: int, main_port: int) -> list:
        """Discover TIS devices on network."""
        discovered_devices = []
        
        try:
            # Parse network range
            if "/" in network_range:
                network_base = network_range.split("/")[0].rsplit(".", 1)[0]
            else:
                network_base = network_range.rsplit(".", 1)[0]
            
            # TIS ports to check (including user's port)
            tis_ports = [main_port, 4001, 4002, 6000, 6001, 8080, 9090]
            # Remove duplicates while preserving order
            tis_ports = list(dict.fromkeys(tis_ports))
            
            _LOGGER.info(f"🔍 Port'lar taranacak: {tis_ports}")
            
            # Scan IP range (limit to smaller range for faster scan)
            for i in range(1, 255):
                ip = f"{network_base}.{i}"
                
                for port in tis_ports:
                    try:
                        # Quick socket test
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(1)  # Quick timeout for scanning
                        result = sock.connect_ex((ip, port))
                        sock.close()
                        
                        if result == 0:
                            _LOGGER.info(f"🎯 Potansiyel TIS cihazı: {ip}:{port}")
                            
                            device_info = {
                                "ip": ip,
                                "port": port,
                                "name": f"TIS Device {ip}",
                                "response": "port_scan_success",
                                "found": True
                            }
                            discovered_devices.append(device_info)
                            break  # One port per IP is enough
                            
                    except Exception:
                        pass
            
        except Exception as err:
            _LOGGER.error(f"Network discovery hatası: {err}")
        
        _LOGGER.info(f"📊 Ağ taraması tamamlandı. {len(discovered_devices)} cihaz bulundu.")
        return discovered_devices

    async def async_step_import(self, user_input: dict[str, Any]) -> FlowResult:
        """Handle import."""
        return await self.async_step_user(user_input)
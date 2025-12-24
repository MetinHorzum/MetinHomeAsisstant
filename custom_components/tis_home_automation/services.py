"""
Services for TIS Home Automation integration.
Custom services for advanced TIS device control and management.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.helpers.device_registry import async_get as async_get_device_registry

from .const import (
    DOMAIN,
    SERVICE_DISCOVER_DEVICES,
    SERVICE_SEND_RAW_COMMAND,
    SERVICE_REFRESH_DEVICE,
    SERVICE_RESET_DEVICE,
    TIS_OPCODES,
    ERROR_MESSAGES,
)
from .coordinator import TISDataUpdateCoordinator
from .entity import TISDeviceWrapper

# Import TIS protocol library
try:
    from .tis_protocol import get_local_ip
    HAS_TIS_PROTOCOL = True
except ImportError:
    HAS_TIS_PROTOCOL = False

_LOGGER = logging.getLogger(__name__)

# Service schemas
DISCOVER_DEVICES_SCHEMA = vol.Schema({
    vol.Optional("source_ip"): cv.string,
    vol.Optional("timeout", default=30.0): vol.All(vol.Coerce(float), vol.Range(min=5.0, max=120.0)),
})

SEND_RAW_COMMAND_SCHEMA = vol.Schema({
    vol.Required("device_id"): vol.Any(cv.string, vol.All(cv.ensure_list, [cv.positive_int])),
    vol.Required("op_code"): vol.Any(cv.string, vol.All(cv.ensure_list, [cv.positive_int])),
    vol.Optional("source_ip"): cv.string,
    vol.Optional("additional_data", default=[]): vol.All(cv.ensure_list, [cv.positive_int]),
})

REFRESH_DEVICE_SCHEMA = vol.Schema({
    vol.Optional("device_id"): cv.string,
    vol.Optional("entity_id"): cv.entity_id,
})

RESET_DEVICE_SCHEMA = vol.Schema({
    vol.Required("device_id"): cv.string,
    vol.Optional("reset_type", default="soft"): vol.In(["soft", "hard", "factory"]),
})

SET_DEVICE_NAME_SCHEMA = vol.Schema({
    vol.Required("device_id"): cv.string,
    vol.Required("name"): cv.string,
})

DEVICE_DIAGNOSTICS_SCHEMA = vol.Schema({
    vol.Optional("device_id"): cv.string,
    vol.Optional("entity_id"): cv.entity_id,
    vol.Optional("include_raw_data", default=False): cv.boolean,
})

SCENE_CONTROL_SCHEMA = vol.Schema({
    vol.Required("device_id"): cv.string,
    vol.Required("scene_id"): vol.All(vol.Coerce(int), vol.Range(min=1, max=16)),
    vol.Optional("action", default="activate"): vol.In(["activate", "store", "delete"]),
})

AC_CONTROL_SCHEMA = vol.Schema({
    vol.Required("device_id"): cv.string,
    vol.Optional("power"): vol.In(["on", "off"]),
    vol.Optional("mode"): vol.In(["cool", "heat", "fan", "auto"]),
    vol.Optional("temperature"): vol.All(vol.Coerce(int), vol.Range(min=16, max=30)),
    vol.Optional("fan_speed"): vol.In(["auto", "low", "medium", "high"]),
})

LIGHTING_CONTROL_SCHEMA = vol.Schema({
    vol.Required("device_id"): cv.string,
    vol.Optional("power"): vol.In(["on", "off"]),
    vol.Optional("brightness"): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
    vol.Optional("gang_index"): vol.All(vol.Coerce(int), vol.Range(min=0, max=3)),
})

class TISServiceManager:
    """Manager for TIS integration services."""
    
    def __init__(self, hass: HomeAssistant):
        """Initialize service manager."""
        self.hass = hass
        self._services_registered = False
    
    async def async_register_services(self):
        """Register all TIS services."""
        if self._services_registered:
            return
        
        # Register core services
        self.hass.services.async_register(
            DOMAIN,
            SERVICE_DISCOVER_DEVICES,
            self._handle_discover_devices,
            schema=DISCOVER_DEVICES_SCHEMA
        )
        
        self.hass.services.async_register(
            DOMAIN,
            SERVICE_SEND_RAW_COMMAND,
            self._handle_send_raw_command,
            schema=SEND_RAW_COMMAND_SCHEMA
        )
        
        self.hass.services.async_register(
            DOMAIN,
            SERVICE_REFRESH_DEVICE,
            self._handle_refresh_device,
            schema=REFRESH_DEVICE_SCHEMA
        )
        
        self.hass.services.async_register(
            DOMAIN,
            SERVICE_RESET_DEVICE,
            self._handle_reset_device,
            schema=RESET_DEVICE_SCHEMA
        )
        
        # Register advanced services
        self.hass.services.async_register(
            DOMAIN,
            "set_device_name",
            self._handle_set_device_name,
            schema=SET_DEVICE_NAME_SCHEMA
        )
        
        self.hass.services.async_register(
            DOMAIN,
            "device_diagnostics",
            self._handle_device_diagnostics,
            schema=DEVICE_DIAGNOSTICS_SCHEMA
        )
        
        self.hass.services.async_register(
            DOMAIN,
            "scene_control",
            self._handle_scene_control,
            schema=SCENE_CONTROL_SCHEMA
        )
        
        self.hass.services.async_register(
            DOMAIN,
            "ac_control",
            self._handle_ac_control,
            schema=AC_CONTROL_SCHEMA
        )
        
        self.hass.services.async_register(
            DOMAIN,
            "lighting_control",
            self._handle_lighting_control,
            schema=LIGHTING_CONTROL_SCHEMA
        )
        
        self._services_registered = True
        _LOGGER.info("TIS services registered successfully")
    
    async def async_unregister_services(self):
        """Unregister all TIS services."""
        if not self._services_registered:
            return
        
        services = [
            SERVICE_DISCOVER_DEVICES,
            SERVICE_SEND_RAW_COMMAND,
            SERVICE_REFRESH_DEVICE,
            SERVICE_RESET_DEVICE,
            "set_device_name",
            "device_diagnostics",
            "scene_control",
            "ac_control",
            "lighting_control",
        ]
        
        for service in services:
            if self.hass.services.has_service(DOMAIN, service):
                self.hass.services.async_remove(DOMAIN, service)
        
        self._services_registered = False
        _LOGGER.info("TIS services unregistered")
    
    def _get_coordinator_from_call(self, call: ServiceCall) -> Optional[TISDataUpdateCoordinator]:
        """Get coordinator from service call."""
        # Get the first available coordinator
        for entry_data in self.hass.data[DOMAIN].values():
            if isinstance(entry_data, dict) and "coordinator" in entry_data:
                return entry_data["coordinator"]
        return None
    
    def _get_device_wrapper(self, coordinator: TISDataUpdateCoordinator, device_id: str) -> Optional[TISDeviceWrapper]:
        """Get device wrapper from device ID."""
        tis_device = coordinator.devices.get(device_id)
        if tis_device:
            return TISDeviceWrapper(tis_device, coordinator)
        return None
    
    async def _handle_discover_devices(self, call: ServiceCall):
        """Handle discover devices service call."""
        try:
            source_ip = call.data.get("source_ip")
            timeout = call.data.get("timeout", 30.0)
            
            if not source_ip and HAS_TIS_PROTOCOL:
                source_ip = get_local_ip()
            elif not source_ip:
                source_ip = "192.168.1.100"  # Fallback
            
            _LOGGER.info(f"Manual device discovery requested (IP: {source_ip}, timeout: {timeout}s)")
            
            # Perform discovery on all coordinators
            discovered_total = 0
            
            for entry_data in self.hass.data[DOMAIN].values():
                if isinstance(entry_data, dict) and "coordinator" in entry_data:
                    coordinator = entry_data["coordinator"]
                    
                    discovered = await coordinator.discover_new_devices(timeout=timeout)
                    discovered_total += len(discovered)
                    
                    # Update discovered devices in entry data
                    if discovered:
                        entry_data["discovered_devices"].update(discovered)
                        await coordinator.async_request_refresh()
            
            _LOGGER.info(f"Manual discovery completed: {discovered_total} new devices found")
            
            # Fire event with results
            self.hass.bus.async_fire(
                f"{DOMAIN}_discovery_completed",
                {
                    "source_ip": source_ip,
                    "timeout": timeout,
                    "devices_found": discovered_total
                }
            )
            
        except Exception as e:
            _LOGGER.error(f"Device discovery service error: {e}")
            self.hass.bus.async_fire(
                f"{DOMAIN}_discovery_error",
                {"error": str(e)}
            )
    
    async def _handle_send_raw_command(self, call: ServiceCall):
        """Handle send raw command service call."""
        try:
            device_id_param = call.data.get("device_id")
            op_code_param = call.data.get("op_code")
            source_ip = call.data.get("source_ip")
            additional_data = call.data.get("additional_data", [])
            
            # Convert parameters to proper format
            if isinstance(device_id_param, str):
                # Convert hex string to byte list
                device_id_param = device_id_param.replace("0x", "").replace(":", "").replace(" ", "")
                if len(device_id_param) == 4:  # 2 bytes
                    device_id = [int(device_id_param[0:2], 16), int(device_id_param[2:4], 16)]
                else:
                    raise ValueError("Invalid device_id format")
            else:
                device_id = list(device_id_param)
            
            if isinstance(op_code_param, str):
                # Convert hex string to byte list
                op_code_param = op_code_param.replace("0x", "").replace(":", "").replace(" ", "")
                if len(op_code_param) == 4:  # 2 bytes
                    op_code = [int(op_code_param[0:2], 16), int(op_code_param[2:4], 16)]
                else:
                    raise ValueError("Invalid op_code format")
            else:
                op_code = list(op_code_param)
            
            if not source_ip and HAS_TIS_PROTOCOL:
                source_ip = get_local_ip()
            elif not source_ip:
                source_ip = "192.168.1.100"
            
            _LOGGER.info(f"Sending raw command - Device: {device_id}, OpCode: {op_code}, Data: {additional_data}")
            
            # Send command on all coordinators
            success_count = 0
            total_count = 0
            
            for entry_data in self.hass.data[DOMAIN].values():
                if isinstance(entry_data, dict) and "coordinator" in entry_data:
                    coordinator = entry_data["coordinator"]
                    communication_manager = entry_data["communication_manager"]
                    
                    total_count += 1
                    
                    result = await communication_manager.send_to_device(
                        device_id=device_id,
                        op_code=op_code,
                        source_ip=source_ip,
                        additional_data=additional_data
                    )
                    
                    if result:
                        success_count += 1
            
            if success_count > 0:
                _LOGGER.info(f"Raw command sent successfully to {success_count}/{total_count} coordinators")
            else:
                _LOGGER.error("Failed to send raw command to any coordinator")
            
            # Fire event with results
            self.hass.bus.async_fire(
                f"{DOMAIN}_command_sent",
                {
                    "device_id": device_id,
                    "op_code": op_code,
                    "additional_data": additional_data,
                    "success_count": success_count,
                    "total_count": total_count
                }
            )
                
        except Exception as e:
            _LOGGER.error(f"Raw command service error: {e}")
            self.hass.bus.async_fire(
                f"{DOMAIN}_command_error",
                {"error": str(e)}
            )
    
    async def _handle_refresh_device(self, call: ServiceCall):
        """Handle refresh device service call."""
        try:
            device_id = call.data.get("device_id")
            entity_id = call.data.get("entity_id")
            
            if entity_id:
                # Get device ID from entity
                entity_registry = async_get_entity_registry(self.hass)
                entity_entry = entity_registry.async_get(entity_id)
                
                if entity_entry and entity_entry.device_id:
                    device_registry = async_get_device_registry(self.hass)
                    device_entry = device_registry.async_get(entity_entry.device_id)
                    
                    if device_entry:
                        # Extract TIS device ID from device identifiers
                        for identifier in device_entry.identifiers:
                            if identifier[0] == DOMAIN:
                                device_id = identifier[1]
                                break
            
            if not device_id:
                _LOGGER.error("No device_id provided and could not determine from entity_id")
                return
            
            _LOGGER.info(f"Refreshing TIS device: {device_id}")
            
            # Refresh device on all coordinators
            refreshed = False
            
            for entry_data in self.hass.data[DOMAIN].values():
                if isinstance(entry_data, dict) and "coordinator" in entry_data:
                    coordinator = entry_data["coordinator"]
                    
                    if device_id in coordinator.devices:
                        # Request device status update
                        device_wrapper = self._get_device_wrapper(coordinator, device_id)
                        if device_wrapper:
                            await device_wrapper.request_status()
                            await coordinator.async_request_refresh()
                            refreshed = True
            
            if refreshed:
                _LOGGER.info(f"Device {device_id} refreshed successfully")
            else:
                _LOGGER.warning(f"Device {device_id} not found or could not be refreshed")
                
        except Exception as e:
            _LOGGER.error(f"Refresh device service error: {e}")
    
    async def _handle_reset_device(self, call: ServiceCall):
        """Handle reset device service call."""
        try:
            device_id = call.data.get("device_id")
            reset_type = call.data.get("reset_type", "soft")
            
            _LOGGER.info(f"Resetting TIS device {device_id} (type: {reset_type})")
            
            # Map reset types to opcodes
            reset_opcodes = {
                "soft": TIS_OPCODES["DEVICE_OFF"],  # Soft reset - turn off/on
                "hard": TIS_OPCODES["DEVICE_INFO_REQUEST"],  # Hard reset - info request
                "factory": TIS_OPCODES["FIRMWARE_VERSION_REQUEST"]  # Factory reset simulation
            }
            
            op_code = reset_opcodes.get(reset_type, TIS_OPCODES["DEVICE_OFF"])
            
            # Send reset command
            reset_success = False
            
            for entry_data in self.hass.data[DOMAIN].values():
                if isinstance(entry_data, dict) and "coordinator" in entry_data:
                    coordinator = entry_data["coordinator"]
                    
                    if device_id in coordinator.devices:
                        device_wrapper = self._get_device_wrapper(coordinator, device_id)
                        if device_wrapper:
                            # Send reset command
                            success = await coordinator.send_device_command(
                                device_key=device_id,
                                op_code=op_code
                            )
                            
                            if success:
                                reset_success = True
                                
                                # For soft reset, also send power on after delay
                                if reset_type == "soft":
                                    import asyncio
                                    await asyncio.sleep(2)
                                    await coordinator.send_device_command(
                                        device_key=device_id,
                                        op_code=TIS_OPCODES["DEVICE_ON"]
                                    )
            
            if reset_success:
                _LOGGER.info(f"Device {device_id} reset successfully")
            else:
                _LOGGER.error(f"Failed to reset device {device_id}")
                
        except Exception as e:
            _LOGGER.error(f"Reset device service error: {e}")
    
    async def _handle_set_device_name(self, call: ServiceCall):
        """Handle set device name service call."""
        try:
            device_id = call.data.get("device_id")
            new_name = call.data.get("name")
            
            _LOGGER.info(f"Setting TIS device {device_id} name to: {new_name}")
            
            # Update device name in coordinator
            updated = False
            
            for entry_data in self.hass.data[DOMAIN].values():
                if isinstance(entry_data, dict) and "coordinator" in entry_data:
                    coordinator = entry_data["coordinator"]
                    
                    if device_id in coordinator.devices:
                        device = coordinator.devices[device_id]
                        device.name = new_name
                        updated = True
                        
                        # Update device registry
                        device_registry = async_get_device_registry(self.hass)
                        device_entry = device_registry.async_get_device(
                            identifiers={(DOMAIN, device_id)}
                        )
                        
                        if device_entry:
                            device_registry.async_update_device(
                                device_entry.id,
                                name=new_name
                            )
            
            if updated:
                _LOGGER.info(f"Device {device_id} name updated to: {new_name}")
            else:
                _LOGGER.error(f"Device {device_id} not found")
                
        except Exception as e:
            _LOGGER.error(f"Set device name service error: {e}")
    
    async def _handle_device_diagnostics(self, call: ServiceCall):
        """Handle device diagnostics service call."""
        try:
            device_id = call.data.get("device_id")
            entity_id = call.data.get("entity_id")
            include_raw_data = call.data.get("include_raw_data", False)
            
            # Get device ID from entity if needed
            if entity_id and not device_id:
                entity_registry = async_get_entity_registry(self.hass)
                entity_entry = entity_registry.async_get(entity_id)
                
                if entity_entry and entity_entry.device_id:
                    device_registry = async_get_device_registry(self.hass)
                    device_entry = device_registry.async_get(entity_entry.device_id)
                    
                    if device_entry:
                        for identifier in device_entry.identifiers:
                            if identifier[0] == DOMAIN:
                                device_id = identifier[1]
                                break
            
            diagnostics = {}
            
            for entry_data in self.hass.data[DOMAIN].values():
                if isinstance(entry_data, dict) and "coordinator" in entry_data:
                    coordinator = entry_data["coordinator"]
                    
                    # Get all devices or specific device
                    devices_to_check = [device_id] if device_id else list(coordinator.devices.keys())
                    
                    for dev_id in devices_to_check:
                        if dev_id in coordinator.devices:
                            device = coordinator.devices[dev_id]
                            device_state = coordinator.get_device_state(dev_id)
                            
                            device_diag = {
                                "device_id": dev_id,
                                "device_name": device.name,
                                "device_type": f"0x{device.device_type:04X}",
                                "device_type_name": coordinator.get_device_by_key(dev_id),
                                "online": coordinator.is_device_online(dev_id),
                                "last_seen": coordinator.device_last_seen.get(dev_id),
                                "ip_address": device.ip_address,
                                "source_address": str(device.source_address),
                            }
                            
                            if device_state:
                                device_diag["current_state"] = device_state
                            
                            if include_raw_data:
                                device_diag["raw_device_data"] = {
                                    "device_id": device.device_id,
                                    "device_type": device.device_type,
                                    "name": device.name,
                                    "ip_address": device.ip_address,
                                    "source_address": device.source_address,
                                }
                            
                            diagnostics[dev_id] = device_diag
            
            # Fire event with diagnostics
            self.hass.bus.async_fire(
                f"{DOMAIN}_diagnostics_completed",
                {
                    "diagnostics": diagnostics,
                    "device_count": len(diagnostics),
                    "include_raw_data": include_raw_data
                }
            )
            
            _LOGGER.info(f"Generated diagnostics for {len(diagnostics)} devices")
                
        except Exception as e:
            _LOGGER.error(f"Device diagnostics service error: {e}")
    
    async def _handle_scene_control(self, call: ServiceCall):
        """Handle scene control service call."""
        try:
            device_id = call.data.get("device_id")
            scene_id = call.data.get("scene_id")
            action = call.data.get("action", "activate")
            
            _LOGGER.info(f"Scene control: {action} scene {scene_id} on device {device_id}")
            
            # Map actions to opcodes
            if action == "activate":
                op_code = TIS_OPCODES["DEVICE_ON"]
                additional_data = [scene_id - 1]  # Convert to 0-based
            elif action == "store":
                op_code = TIS_OPCODES["DEVICE_INFO_REQUEST"]  # Use info request for store
                additional_data = [scene_id - 1, 1]  # Store flag
            elif action == "delete":
                op_code = TIS_OPCODES["DEVICE_OFF"]  # Use off for delete
                additional_data = [scene_id - 1]
            else:
                _LOGGER.error(f"Unknown scene action: {action}")
                return
            
            # Send scene command
            success = False
            
            for entry_data in self.hass.data[DOMAIN].values():
                if isinstance(entry_data, dict) and "coordinator" in entry_data:
                    coordinator = entry_data["coordinator"]
                    
                    if device_id in coordinator.devices:
                        result = await coordinator.send_device_command(
                            device_key=device_id,
                            op_code=op_code,
                            additional_data=additional_data
                        )
                        
                        if result:
                            success = True
            
            if success:
                _LOGGER.info(f"Scene {action} command sent successfully")
            else:
                _LOGGER.error(f"Failed to send scene {action} command")
                
        except Exception as e:
            _LOGGER.error(f"Scene control service error: {e}")
    
    async def _handle_ac_control(self, call: ServiceCall):
        """Handle AC control service call."""
        try:
            device_id = call.data.get("device_id")
            power = call.data.get("power")
            mode = call.data.get("mode")
            temperature = call.data.get("temperature")
            fan_speed = call.data.get("fan_speed")
            
            _LOGGER.info(f"AC control for device {device_id}")
            
            coordinator = self._get_coordinator_from_call(call)
            if not coordinator or device_id not in coordinator.devices:
                _LOGGER.error(f"Device {device_id} not found")
                return
            
            # Send power command
            if power is not None:
                if power == "on":
                    op_code = TIS_OPCODES["AC_POWER_ON"]
                else:
                    op_code = TIS_OPCODES["AC_POWER_OFF"]
                
                await coordinator.send_device_command(
                    device_key=device_id,
                    op_code=op_code
                )
            
            # Send mode command
            if mode is not None:
                mode_mapping = {"cool": 0, "heat": 1, "fan": 2, "auto": 3}
                mode_value = mode_mapping.get(mode, 3)
                
                await coordinator.send_device_command(
                    device_key=device_id,
                    op_code=TIS_OPCODES["AC_SET_MODE"],
                    additional_data=[mode_value]
                )
            
            # Send temperature command
            if temperature is not None:
                await coordinator.send_device_command(
                    device_key=device_id,
                    op_code=TIS_OPCODES["AC_SET_TEMPERATURE"],
                    additional_data=[temperature]
                )
            
            # Send fan speed command
            if fan_speed is not None:
                fan_mapping = {"auto": 0, "low": 1, "medium": 2, "high": 3}
                fan_value = fan_mapping.get(fan_speed, 0)
                
                await coordinator.send_device_command(
                    device_key=device_id,
                    op_code=TIS_OPCODES["AC_SET_FAN_SPEED"],
                    additional_data=[fan_value]
                )
            
            _LOGGER.info(f"AC control commands sent to device {device_id}")
                
        except Exception as e:
            _LOGGER.error(f"AC control service error: {e}")
    
    async def _handle_lighting_control(self, call: ServiceCall):
        """Handle lighting control service call."""
        try:
            device_id = call.data.get("device_id")
            power = call.data.get("power")
            brightness = call.data.get("brightness")
            gang_index = call.data.get("gang_index", 0)
            
            _LOGGER.info(f"Lighting control for device {device_id}, gang {gang_index}")
            
            coordinator = self._get_coordinator_from_call(call)
            if not coordinator or device_id not in coordinator.devices:
                _LOGGER.error(f"Device {device_id} not found")
                return
            
            # Send power command
            if power is not None:
                if power == "on":
                    if brightness is not None:
                        # Send dimmer command
                        op_code = TIS_OPCODES["LIGHT_DIMMER"]
                        additional_data = [gang_index, brightness] if gang_index > 0 else [brightness]
                    else:
                        # Send on command
                        op_code = TIS_OPCODES["LIGHT_ON"]
                        additional_data = [gang_index] if gang_index > 0 else []
                else:
                    # Send off command
                    op_code = TIS_OPCODES["LIGHT_OFF"]
                    additional_data = [gang_index] if gang_index > 0 else []
                
                await coordinator.send_device_command(
                    device_key=device_id,
                    op_code=op_code,
                    additional_data=additional_data
                )
            
            # Send brightness command only
            elif brightness is not None:
                await coordinator.send_device_command(
                    device_key=device_id,
                    op_code=TIS_OPCODES["LIGHT_DIMMER"],
                    additional_data=[gang_index, brightness] if gang_index > 0 else [brightness]
                )
            
            _LOGGER.info(f"Lighting control commands sent to device {device_id}")
                
        except Exception as e:
            _LOGGER.error(f"Lighting control service error: {e}")
"""
Data Update Coordinator for TIS Home Automation integration.
Manages device state updates and communication with TIS devices.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util.dt import utcnow

from .const import (
    DOMAIN,
    TIS_OPCODES,
    TIS_DEVICE_TYPES,
    ERROR_MESSAGES,
    EVENT_TIS_DEVICE_DISCOVERED,
    EVENT_TIS_DEVICE_LOST,
    EVENT_TIS_COMMUNICATION_ERROR,
    UPDATE_INTERVALS
)

# Import TIS protocol library
try:
    from .tis_protocol import (
        TISCommunicationManager,
        TISDevice,
        TISCommunicationError,
        TISTimeoutError,
        get_local_ip
    )
    HAS_TIS_PROTOCOL = True
except ImportError:
    HAS_TIS_PROTOCOL = False

_LOGGER = logging.getLogger(__name__)

class TISDataUpdateCoordinator(DataUpdateCoordinator):
    """Coordinator for TIS device data updates."""
    
    def __init__(
        self,
        hass: HomeAssistant,
        communication_manager: TISCommunicationManager,
        update_interval: timedelta
    ) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )
        
        self.communication_manager = communication_manager
        self.devices: Dict[str, TISDevice] = {}
        self.device_states: Dict[str, Dict[str, Any]] = {}
        self.device_last_seen: Dict[str, datetime] = {}
        self.offline_devices: set = set()
        
        # Track update intervals per device type
        self._device_update_intervals: Dict[str, int] = {}
        self._last_update_times: Dict[str, datetime] = {}
        
        # Setup periodic tasks
        self._setup_periodic_tasks()
    
    def _setup_periodic_tasks(self):
        """Setup periodic background tasks."""
        # Device health check every 5 minutes
        async_track_time_interval(
            self.hass,
            self._check_device_health,
            timedelta(minutes=5)
        )
        
        # Rediscover offline devices every 10 minutes
        async_track_time_interval(
            self.hass,
            self._rediscover_offline_devices,
            timedelta(minutes=10)
        )
    
    async def _async_update_data(self) -> Dict[str, Any]:
        """Update data from TIS devices."""
        try:
            updated_data = {}
            
            # Update each device based on its specific interval
            current_time = utcnow()
            
            for device_id, device in self.devices.items():
                try:
                    # Check if device needs update based on its type-specific interval
                    device_type = device.device_type
                    device_type_name = TIS_DEVICE_TYPES.get(device_type, "unknown_device")
                    
                    update_interval = UPDATE_INTERVALS.get(
                        self._get_primary_platform(device_type_name),
                        60  # Default 60 seconds
                    )
                    
                    last_update = self._last_update_times.get(device_id)
                    if (last_update and 
                        current_time - last_update < timedelta(seconds=update_interval)):
                        # Skip this device for now, use cached data
                        updated_data[device_id] = self.device_states.get(device_id, {})
                        continue
                    
                    # Update device state
                    device_data = await self._update_device_state(device)
                    if device_data:
                        updated_data[device_id] = device_data
                        self.device_states[device_id] = device_data
                        self.device_last_seen[device_id] = current_time
                        self._last_update_times[device_id] = current_time
                        
                        # Remove from offline devices if it was there
                        self.offline_devices.discard(device_id)
                    else:
                        # Device didn't respond, mark as potentially offline
                        if device_id not in self.offline_devices:
                            _LOGGER.warning(f"TIS device {device_id} not responding")
                            self.offline_devices.add(device_id)
                        
                        # Use last known state
                        updated_data[device_id] = self.device_states.get(device_id, {})
                
                except Exception as e:
                    _LOGGER.error(f"Error updating TIS device {device_id}: {e}")
                    # Use last known state on error
                    updated_data[device_id] = self.device_states.get(device_id, {})
            
            return updated_data
            
        except Exception as e:
            _LOGGER.error(f"Error updating TIS coordinator data: {e}")
            raise UpdateFailed(f"TIS coordinator update failed: {e}")
    
    async def _update_device_state(self, device: TISDevice) -> Optional[Dict[str, Any]]:
        """Update state for a specific TIS device."""
        try:
            device_id = device.device_id
            device_type = device.device_type
            device_key = f"{device_id[0]:02X}{device_id[1]:02X}"
            
            # Determine appropriate status request based on device type
            device_type_name = TIS_DEVICE_TYPES.get(device_type, "unknown_device")
            
            if "switch" in device_type_name or "dimmer" in device_type_name:
                # Request lighting status
                op_code = TIS_OPCODES["LIGHT_STATUS"]
            elif "ac_controller" in device_type_name or "thermostat" in device_type_name:
                # Request AC status  
                op_code = TIS_OPCODES["AC_STATUS_REQUEST"]
            elif "sensor" in device_type_name:
                # Request sensor data
                op_code = TIS_OPCODES["SENSOR_DATA_REQUEST"]
            else:
                # Generic device status request
                op_code = TIS_OPCODES["DEVICE_STATUS_REQUEST"]
            
            # Send status request
            local_ip = get_local_ip()
            success = await self.communication_manager.send_to_device(
                device_id=device_id,
                op_code=op_code,
                source_ip=local_ip
            )
            
            if not success:
                _LOGGER.debug(f"Failed to send status request to device {device_key}")
                return None
            
            # Wait for response (this would be handled by communication manager callbacks in real implementation)
            # For now, return basic device info
            device_data = {
                "device_id": device_key,
                "device_type": device_type,
                "device_type_name": device_type_name,
                "name": device.name,
                "online": True,
                "last_seen": utcnow().isoformat(),
                "ip_address": device.ip_address,
                "source_address": str(device.source_address) if device.source_address else None,
            }
            
            # Add device-specific state information
            if "switch" in device_type_name:
                # Simulate switch states (in real implementation, this comes from device response)
                gang_count = int(device_type_name.split("_")[1][0]) if "_" in device_type_name else 1
                device_data["switches"] = [{"state": "unknown"} for _ in range(gang_count)]
            
            elif "dimmer" in device_type_name:
                # Simulate dimmer states
                gang_count = int(device_type_name.split("_")[1][0]) if "_" in device_type_name else 1
                device_data["dimmers"] = [
                    {"state": "unknown", "brightness": 0} for _ in range(gang_count)
                ]
            
            elif "ac_controller" in device_type_name:
                # Simulate AC state
                device_data["ac"] = {
                    "power": "unknown",
                    "temperature": 24,
                    "mode": "cool",
                    "fan_speed": "auto"
                }
            
            elif "sensor" in device_type_name:
                # Simulate sensor data
                if "health_sensor" in device_type_name:
                    device_data["sensors"] = {
                        "lux": 0,
                        "noise": 0,
                        "eco2": 400,
                        "tvoc": 0,
                        "temperature": 25,
                        "humidity": 50
                    }
                elif "temperature" in device_type_name:
                    device_data["temperature"] = 25.0
                elif "humidity" in device_type_name:
                    device_data["humidity"] = 50.0
                elif "motion" in device_type_name:
                    device_data["motion"] = False
                elif "door_window" in device_type_name:
                    device_data["contact"] = True
            
            return device_data
            
        except Exception as e:
            _LOGGER.error(f"Error updating device state for {device.name}: {e}")
            return None
    
    def _get_primary_platform(self, device_type_name: str) -> str:
        """Get primary platform type for update interval."""
        if "switch" in device_type_name:
            return "switch"
        elif "dimmer" in device_type_name:
            return "light"
        elif "ac_controller" in device_type_name or "thermostat" in device_type_name:
            return "climate"
        elif "sensor" in device_type_name:
            return "sensor"
        elif "motion" in device_type_name or "door" in device_type_name:
            return "binary_sensor"
        else:
            return "sensor"
    
    async def add_device(self, device: TISDevice) -> None:
        """Add a new TIS device to coordinator."""
        device_key = f"{device.device_id[0]:02X}{device.device_id[1]:02X}"
        
        if device_key not in self.devices:
            self.devices[device_key] = device
            _LOGGER.info(f"Added TIS device: {device.name} ({device_key})")
            
            # Fire device discovered event
            self.hass.bus.async_fire(
                EVENT_TIS_DEVICE_DISCOVERED,
                {
                    "device_id": device_key,
                    "device_type": device.device_type,
                    "device_name": device.name,
                    "ip_address": device.ip_address
                }
            )
            
            # Trigger coordinator update
            await self.async_request_refresh()
    
    async def remove_device(self, device_key: str) -> None:
        """Remove a TIS device from coordinator."""
        if device_key in self.devices:
            device = self.devices.pop(device_key)
            self.device_states.pop(device_key, None)
            self.device_last_seen.pop(device_key, None)
            self.offline_devices.discard(device_key)
            
            _LOGGER.info(f"Removed TIS device: {device.name} ({device_key})")
            
            # Fire device lost event
            self.hass.bus.async_fire(
                EVENT_TIS_DEVICE_LOST,
                {
                    "device_id": device_key,
                    "device_name": device.name
                }
            )
    
    async def send_device_command(
        self,
        device_key: str,
        op_code: List[int],
        additional_data: Optional[List[int]] = None
    ) -> bool:
        """Send command to specific TIS device."""
        try:
            device = self.devices.get(device_key)
            if not device:
                _LOGGER.error(f"Device {device_key} not found")
                return False
            
            local_ip = get_local_ip()
            success = await self.communication_manager.send_to_device(
                device_id=device.device_id,
                op_code=op_code,
                source_ip=local_ip,
                additional_data=additional_data or []
            )
            
            if success:
                # Mark device as seen and request update
                self.device_last_seen[device_key] = utcnow()
                self.offline_devices.discard(device_key)
                await self.async_request_refresh()
            
            return success
            
        except Exception as e:
            _LOGGER.error(f"Error sending command to device {device_key}: {e}")
            return False
    
    async def discover_new_devices(self, timeout: float = 30.0) -> Dict[str, TISDevice]:
        """Discover new TIS devices."""
        try:
            local_ip = get_local_ip()
            discovered = await self.communication_manager.discover_devices(
                source_ip=local_ip,
                timeout=timeout
            )
            
            # Add new devices to coordinator
            new_devices = {}
            for device_key, device in discovered.items():
                if device_key not in self.devices:
                    await self.add_device(device)
                    new_devices[device_key] = device
            
            _LOGGER.info(f"Discovered {len(new_devices)} new TIS devices")
            return new_devices
            
        except Exception as e:
            _LOGGER.error(f"Error during device discovery: {e}")
            return {}
    
    @callback
    async def _check_device_health(self, now: datetime) -> None:
        """Check health of all devices and mark offline ones."""
        try:
            offline_threshold = timedelta(minutes=10)
            
            for device_key, last_seen in self.device_last_seen.items():
                if now - last_seen > offline_threshold:
                    if device_key not in self.offline_devices:
                        device = self.devices.get(device_key)
                        device_name = device.name if device else device_key
                        
                        _LOGGER.warning(f"TIS device {device_name} ({device_key}) appears offline")
                        self.offline_devices.add(device_key)
                        
                        # Fire communication error event
                        self.hass.bus.async_fire(
                            EVENT_TIS_COMMUNICATION_ERROR,
                            {
                                "device_id": device_key,
                                "device_name": device_name,
                                "error": "Device offline - no response"
                            }
                        )
        
        except Exception as e:
            _LOGGER.error(f"Error checking device health: {e}")
    
    @callback 
    async def _rediscover_offline_devices(self, now: datetime) -> None:
        """Attempt to rediscover offline devices."""
        if not self.offline_devices:
            return
        
        try:
            _LOGGER.info(f"Attempting to rediscover {len(self.offline_devices)} offline devices")
            
            # Perform discovery to see if offline devices come back online
            discovered = await self.discover_new_devices(timeout=10.0)
            
            # Check if any offline devices were rediscovered
            rediscovered = []
            for device_key in list(self.offline_devices):
                if device_key in discovered or device_key in self.devices:
                    # Try to update device state
                    device = self.devices.get(device_key)
                    if device:
                        device_data = await self._update_device_state(device)
                        if device_data:
                            self.offline_devices.discard(device_key)
                            rediscovered.append(device_key)
                            _LOGGER.info(f"TIS device {device.name} ({device_key}) is back online")
            
            if rediscovered:
                await self.async_request_refresh()
                
        except Exception as e:
            _LOGGER.error(f"Error rediscovering offline devices: {e}")
    
    def get_device_state(self, device_key: str) -> Optional[Dict[str, Any]]:
        """Get current state for a device."""
        return self.device_states.get(device_key)
    
    def is_device_online(self, device_key: str) -> bool:
        """Check if a device is online."""
        return device_key not in self.offline_devices
    
    def get_all_devices(self) -> Dict[str, TISDevice]:
        """Get all managed devices."""
        return self.devices.copy()
    
    def get_devices_by_type(self, device_type: str) -> List[TISDevice]:
        """Get devices by type name."""
        return [
            device for device in self.devices.values()
            if TIS_DEVICE_TYPES.get(device.device_type, "unknown_device") == device_type
        ]
    
    async def async_shutdown(self) -> None:
        """Shutdown coordinator and cleanup resources."""
        try:
            # Disconnect communication manager
            if self.communication_manager:
                await self.communication_manager.disconnect_all()
            
            # Clear device data
            self.devices.clear()
            self.device_states.clear()
            self.device_last_seen.clear()
            self.offline_devices.clear()
            
            _LOGGER.info("TIS coordinator shutdown completed")
            
        except Exception as e:
            _LOGGER.error(f"Error during coordinator shutdown: {e}")
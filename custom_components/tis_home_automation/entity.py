"""
Base entity class for TIS Home Automation devices.
Provides common functionality for all TIS device entities.
"""
from __future__ import annotations

import logging
from abc import abstractmethod
from typing import Any, Dict, List, Optional, Callable

from homeassistant.const import (
    ATTR_IDENTIFIERS,
    ATTR_MANUFACTURER,
    ATTR_MODEL,
    ATTR_NAME,
    ATTR_SW_VERSION,
    ATTR_VIA_DEVICE,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from homeassistant.util.dt import utcnow

from .const import (
    DOMAIN,
    TIS_DEVICE_TYPES,
    TIS_OPCODES,
    ATTR_DEVICE_ID,
    ATTR_DEVICE_TYPE,
    ATTR_FIRMWARE_VERSION,
    ATTR_SIGNAL_STRENGTH,
    ATTR_LAST_SEEN,
    ATTR_COMMUNICATION_TYPE,
    ATTR_SOURCE_ADDRESS,
)
from .coordinator import TISDataUpdateCoordinator

# Import TIS protocol library
try:
    from tis_protocol import TISDevice
    HAS_TIS_PROTOCOL = True
except ImportError:
    HAS_TIS_PROTOCOL = False

_LOGGER = logging.getLogger(__name__)

class TISBaseEntity(CoordinatorEntity[TISDataUpdateCoordinator]):
    """Base class for all TIS device entities."""
    
    def __init__(
        self,
        coordinator: TISDataUpdateCoordinator,
        device_key: str,
        entity_key: str,
        entity_name: str,
        entity_type: str,
        icon: Optional[str] = None,
        device_class: Optional[str] = None,
        unit_of_measurement: Optional[str] = None,
    ) -> None:
        """Initialize TIS base entity."""
        super().__init__(coordinator)
        
        self.device_key = device_key
        self.entity_key = entity_key
        self.entity_type = entity_type
        self._icon = icon
        self._device_class = device_class
        self._unit_of_measurement = unit_of_measurement
        
        # Get TIS device from coordinator
        self.tis_device: Optional[TISDevice] = coordinator.devices.get(device_key)
        
        if not self.tis_device:
            _LOGGER.error(f"TIS device {device_key} not found in coordinator")
            return
        
        # Generate unique entity ID
        device_type_name = TIS_DEVICE_TYPES.get(
            self.tis_device.device_type, 
            "unknown_device"
        )
        
        self._attr_unique_id = f"{DOMAIN}_{device_key}_{entity_key}"
        self._attr_name = entity_name
        
        # Set entity attributes
        self._attr_should_poll = False  # We use coordinator
        self._attr_available = True
        
        # Set entity specific attributes
        if icon:
            self._attr_icon = icon
        if device_class:
            self._attr_device_class = device_class
        if unit_of_measurement:
            self._attr_unit_of_measurement = unit_of_measurement
    
    @property
    def device_info(self) -> DeviceInfo:
        """Return device registry information for this entity."""
        if not self.tis_device:
            return None
        
        device_type_name = TIS_DEVICE_TYPES.get(
            self.tis_device.device_type,
            f"Unknown ({self.tis_device.device_type:04X})"
        )
        
        return DeviceInfo(
            identifiers={(DOMAIN, self.device_key)},
            name=self.tis_device.name,
            manufacturer="TIS Smart Home",
            model=device_type_name,
            sw_version=getattr(self.tis_device, 'firmware_version', "Unknown"),
            via_device=None,  # Direct connection
        )
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        if not self.tis_device:
            return {}
        
        device_state = self.coordinator.get_device_state(self.device_key)
        
        attrs = {
            ATTR_DEVICE_ID: self.device_key,
            ATTR_DEVICE_TYPE: f"0x{self.tis_device.device_type:04X}",
            ATTR_LAST_SEEN: device_state.get("last_seen") if device_state else None,
            ATTR_COMMUNICATION_TYPE: self.coordinator.communication_manager.__class__.__name__,
        }
        
        # Add device-specific attributes
        if self.tis_device.ip_address:
            attrs["ip_address"] = self.tis_device.ip_address
        
        if self.tis_device.source_address:
            attrs[ATTR_SOURCE_ADDRESS] = str(self.tis_device.source_address)
        
        # Add firmware version if available
        if device_state and "firmware_version" in device_state:
            attrs[ATTR_FIRMWARE_VERSION] = device_state["firmware_version"]
        
        return attrs
    
    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        if not self.coordinator.last_update_success:
            return False
        
        return self.coordinator.is_device_online(self.device_key)
    
    async def async_send_command(
        self,
        op_code: List[int],
        additional_data: Optional[List[int]] = None
    ) -> bool:
        """Send command to TIS device."""
        try:
            success = await self.coordinator.send_device_command(
                device_key=self.device_key,
                op_code=op_code,
                additional_data=additional_data or []
            )
            
            if success:
                # Request coordinator refresh after successful command
                await self.coordinator.async_request_refresh()
            
            return success
            
        except Exception as e:
            _LOGGER.error(f"Error sending command to {self.entity_id}: {e}")
            return False
    
    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # Update availability based on device online status
        self._attr_available = self.coordinator.is_device_online(self.device_key)
        
        # Call platform-specific update handler
        self._update_from_coordinator_data()
        
        # Schedule entity update
        self.async_write_ha_state()
    
    @abstractmethod
    def _update_from_coordinator_data(self) -> None:
        """Update entity state from coordinator data.
        
        This method should be implemented by each entity type
        to extract relevant state information from coordinator data.
        """
        pass
    
    async def async_refresh(self) -> None:
        """Manually refresh entity data."""
        await self.coordinator.async_request_refresh()

class TISMultiChannelEntity(TISBaseEntity):
    """Base class for multi-channel TIS devices (e.g., multi-gang switches)."""
    
    def __init__(
        self,
        coordinator: TISDataUpdateCoordinator,
        device_key: str,
        channel_index: int,
        entity_name: str,
        entity_type: str,
        icon: Optional[str] = None,
        device_class: Optional[str] = None,
        unit_of_measurement: Optional[str] = None,
    ) -> None:
        """Initialize multi-channel TIS entity."""
        
        # Create entity key with channel index
        entity_key = f"{entity_type}_{channel_index}"
        
        super().__init__(
            coordinator=coordinator,
            device_key=device_key,
            entity_key=entity_key,
            entity_name=f"{entity_name} {channel_index + 1}",  # 1-based naming
            entity_type=entity_type,
            icon=icon,
            device_class=device_class,
            unit_of_measurement=unit_of_measurement
        )
        
        self.channel_index = channel_index
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes including channel info."""
        attrs = super().extra_state_attributes
        attrs["channel"] = self.channel_index + 1  # 1-based for display
        return attrs
    
    def get_channel_data(self, data_key: str) -> Any:
        """Get data for this specific channel from coordinator."""
        device_state = self.coordinator.get_device_state(self.device_key)
        if not device_state:
            return None
        
        channel_data = device_state.get(data_key, [])
        if isinstance(channel_data, list) and len(channel_data) > self.channel_index:
            return channel_data[self.channel_index]
        
        return None

class TISSensorEntity(TISBaseEntity):
    """Base class for TIS sensor entities."""
    
    def __init__(
        self,
        coordinator: TISDataUpdateCoordinator,
        device_key: str,
        sensor_key: str,
        sensor_name: str,
        icon: Optional[str] = None,
        device_class: Optional[str] = None,
        unit_of_measurement: Optional[str] = None,
        state_class: Optional[str] = None,
    ) -> None:
        """Initialize TIS sensor entity."""
        
        super().__init__(
            coordinator=coordinator,
            device_key=device_key,
            entity_key=sensor_key,
            entity_name=sensor_name,
            entity_type="sensor",
            icon=icon,
            device_class=device_class,
            unit_of_measurement=unit_of_measurement
        )
        
        self.sensor_key = sensor_key
        
        # Set state class for sensors
        if state_class:
            self._attr_state_class = state_class
    
    @property
    def state(self) -> Any:
        """Return the state of the sensor."""
        device_state = self.coordinator.get_device_state(self.device_key)
        if not device_state:
            return None
        
        # Handle multi-sensor devices (like health sensor)
        if "sensors" in device_state:
            sensors_data = device_state["sensors"]
            if isinstance(sensors_data, dict):
                return sensors_data.get(self.sensor_key)
        
        # Handle single sensor devices
        return device_state.get(self.sensor_key)
    
    def _update_from_coordinator_data(self) -> None:
        """Update sensor state from coordinator data."""
        # Sensor state is handled by the state property
        pass

class TISDeviceWrapper:
    """Wrapper class for TIS devices to provide additional functionality."""
    
    def __init__(self, tis_device: TISDevice, coordinator: TISDataUpdateCoordinator):
        """Initialize device wrapper."""
        self.tis_device = tis_device
        self.coordinator = coordinator
        self.device_key = f"{tis_device.device_id[0]:02X}{tis_device.device_id[1]:02X}"
    
    @property
    def device_type_name(self) -> str:
        """Get human-readable device type name."""
        return TIS_DEVICE_TYPES.get(
            self.tis_device.device_type,
            f"unknown_{self.tis_device.device_type:04X}"
        )
    
    @property
    def is_online(self) -> bool:
        """Check if device is online."""
        return self.coordinator.is_device_online(self.device_key)
    
    @property
    def last_seen(self) -> Optional[str]:
        """Get last seen timestamp."""
        device_state = self.coordinator.get_device_state(self.device_key)
        return device_state.get("last_seen") if device_state else None
    
    async def send_discovery_request(self) -> bool:
        """Send discovery request to device."""
        return await self.coordinator.send_device_command(
            device_key=self.device_key,
            op_code=TIS_OPCODES["DEVICE_DISCOVERY"]
        )
    
    async def send_info_request(self) -> bool:
        """Send device info request."""
        return await self.coordinator.send_device_command(
            device_key=self.device_key,
            op_code=TIS_OPCODES["DEVICE_INFO_REQUEST"]
        )
    
    async def send_firmware_version_request(self) -> bool:
        """Send firmware version request."""
        return await self.coordinator.send_device_command(
            device_key=self.device_key,
            op_code=TIS_OPCODES["FIRMWARE_VERSION_REQUEST"]
        )
    
    async def power_on(self) -> bool:
        """Turn device on."""
        return await self.coordinator.send_device_command(
            device_key=self.device_key,
            op_code=TIS_OPCODES["DEVICE_ON"]
        )
    
    async def power_off(self) -> bool:
        """Turn device off."""
        return await self.coordinator.send_device_command(
            device_key=self.device_key,
            op_code=TIS_OPCODES["DEVICE_OFF"]
        )
    
    async def request_status(self) -> bool:
        """Request device status."""
        return await self.coordinator.send_device_command(
            device_key=self.device_key,
            op_code=TIS_OPCODES["DEVICE_STATUS_REQUEST"]
        )
    
    def get_state_data(self) -> Optional[Dict[str, Any]]:
        """Get current device state data."""
        return self.coordinator.get_device_state(self.device_key)
    
    def __str__(self) -> str:
        """String representation of device wrapper."""
        return f"TISDevice({self.device_key}, {self.device_type_name}, {self.tis_device.name})"
    
    def __repr__(self) -> str:
        """Detailed representation of device wrapper."""
        return (
            f"TISDeviceWrapper("
            f"device_key={self.device_key}, "
            f"device_type=0x{self.tis_device.device_type:04X}, "
            f"name='{self.tis_device.name}', "
            f"online={self.is_online})"
        )

# Utility functions for entity creation

def create_device_entities(
    hass: HomeAssistant,
    coordinator: TISDataUpdateCoordinator,
    device_wrapper: TISDeviceWrapper,
    platform: str
) -> List[Entity]:
    """Create entities for a TIS device based on its capabilities."""
    from .const import DEVICE_CAPABILITIES
    
    entities = []
    device_type_name = device_wrapper.device_type_name
    device_key = device_wrapper.device_key
    
    # Get device capabilities
    capabilities = DEVICE_CAPABILITIES.get(device_type_name, ["sensor"])
    
    for i, capability in enumerate(capabilities):
        if capability != platform:
            continue
        
        entity_name = f"{device_wrapper.tis_device.name}"
        
        # Handle multi-channel devices
        if len(capabilities) > 1 and capabilities.count(capability) > 1:
            # Multiple entities of same type
            channel_count = sum(1 for c in capabilities[:i+1] if c == capability)
            entity_name += f" {capability.title()} {channel_count}"
        elif len(capabilities) > 1:
            # Single entity of this type in multi-capability device
            entity_name += f" {capability.title()}"
        
        # Create platform-specific entity
        if platform == "switch":
            from .switch import TISSwitchEntity
            entity = TISSwitchEntity(
                coordinator=coordinator,
                device_key=device_key,
                entity_key=f"switch_{i}",
                entity_name=entity_name
            )
        elif platform == "light":
            from .light import TISLightEntity
            entity = TISLightEntity(
                coordinator=coordinator,
                device_key=device_key,
                entity_key=f"light_{i}",
                entity_name=entity_name
            )
        elif platform == "sensor":
            from .sensor import create_sensor_entities_for_device
            sensor_entities = create_sensor_entities_for_device(
                coordinator, device_wrapper, i
            )
            entities.extend(sensor_entities)
            continue
        elif platform == "binary_sensor":
            from .binary_sensor import TISBinarySensorEntity
            entity = TISBinarySensorEntity(
                coordinator=coordinator,
                device_key=device_key,
                entity_key=f"binary_sensor_{i}",
                entity_name=entity_name
            )
        elif platform == "climate":
            from .climate import TISClimateEntity
            entity = TISClimateEntity(
                coordinator=coordinator,
                device_key=device_key,
                entity_key=f"climate_{i}",
                entity_name=entity_name
            )
        else:
            continue
        
        entities.append(entity)
    
    return entities
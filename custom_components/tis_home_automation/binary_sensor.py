"""
Binary sensor platform for TIS Home Automation integration.
Supports TIS binary sensor devices like motion detectors, door sensors, etc.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    TIS_DEVICE_TYPES,
    TIS_OPCODES,
    DEVICE_CAPABILITIES,
    ENTITY_DEFINITIONS,
)
from .coordinator import TISDataUpdateCoordinator
from .entity import TISBaseEntity, TISDeviceWrapper

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up TIS binary sensor entities from config entry."""
    
    # Get coordinator and devices from hass data
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    coordinator: TISDataUpdateCoordinator = entry_data["coordinator"]
    discovered_devices = entry_data["discovered_devices"]
    
    entities = []
    
    # Create binary sensor entities for each discovered device
    for device_key, tis_device in discovered_devices.items():
        device_wrapper = TISDeviceWrapper(tis_device, coordinator)
        device_type_name = device_wrapper.device_type_name
        
        # Check if device has binary sensor capabilities
        capabilities = DEVICE_CAPABILITIES.get(device_type_name, [])
        
        binary_sensor_indices = [i for i, cap in enumerate(capabilities) if cap == "binary_sensor"]
        
        for binary_sensor_index in binary_sensor_indices:
            # Create binary sensor entity based on device type
            entity = create_binary_sensor_entity_for_device(
                coordinator, device_wrapper, binary_sensor_index
            )
            if entity:
                entities.append(entity)
                _LOGGER.debug(f"Added TIS binary sensor entity: {entity.name}")
    
    if entities:
        async_add_entities(entities, True)
        _LOGGER.info(f"Added {len(entities)} TIS binary sensor entities")

def create_binary_sensor_entity_for_device(
    coordinator: TISDataUpdateCoordinator,
    device_wrapper: TISDeviceWrapper,
    sensor_index: int = 0
) -> Optional[TISBinarySensorEntity]:
    """Create binary sensor entity for a TIS device based on its type."""
    
    device_type_name = device_wrapper.device_type_name
    device_key = device_wrapper.device_key
    device_name = device_wrapper.tis_device.name
    
    # Motion sensor
    if "motion_sensor" in device_type_name:
        return TISMotionSensorEntity(
            coordinator=coordinator,
            device_key=device_key,
            device_name=device_name
        )
    
    # Door/window sensor
    elif "door_window_sensor" in device_type_name:
        return TISDoorWindowSensorEntity(
            coordinator=coordinator,
            device_key=device_key,
            device_name=device_name
        )
    
    # Smoke detector
    elif "smoke_detector" in device_type_name:
        return TISSmokeDetectorEntity(
            coordinator=coordinator,
            device_key=device_key,
            device_name=device_name
        )
    
    # Gas detector
    elif "gas_detector" in device_type_name:
        return TISGasDetectorEntity(
            coordinator=coordinator,
            device_key=device_key,
            device_name=device_name
        )
    
    # Security/alarm related sensors
    elif "alarm" in device_type_name or "security" in device_type_name:
        return TISSecuritySensorEntity(
            coordinator=coordinator,
            device_key=device_key,
            device_name=device_name,
            sensor_index=sensor_index
        )
    
    # Generic binary sensor fallback
    else:
        return TISGenericBinarySensorEntity(
            coordinator=coordinator,
            device_key=device_key,
            device_name=device_name,
            sensor_index=sensor_index
        )

class TISBinarySensorEntity(TISBaseEntity, BinarySensorEntity):
    """Base class for TIS binary sensor entities."""
    
    def __init__(
        self,
        coordinator: TISDataUpdateCoordinator,
        device_key: str,
        entity_key: str,
        entity_name: str,
        device_class: Optional[BinarySensorDeviceClass] = None,
        icon_on: Optional[str] = None,
        icon_off: Optional[str] = None,
    ) -> None:
        """Initialize TIS binary sensor entity."""
        
        super().__init__(
            coordinator=coordinator,
            device_key=device_key,
            entity_key=entity_key,
            entity_name=entity_name,
            entity_type="binary_sensor",
            icon=icon_off,  # Default to off icon
            device_class=device_class
        )
        
        # Binary sensor state
        self._is_on = False
        self._icon_on = icon_on
        self._icon_off = icon_off
        
        # Set device class
        if device_class:
            self._attr_device_class = device_class
    
    @property
    def is_on(self) -> bool:
        """Return True if the binary sensor is on."""
        return self._is_on
    
    @property
    def icon(self) -> Optional[str]:
        """Return icon based on state."""
        if self._is_on and self._icon_on:
            return self._icon_on
        elif not self._is_on and self._icon_off:
            return self._icon_off
        else:
            return super().icon
    
    def _update_from_coordinator_data(self) -> None:
        """Update binary sensor state from coordinator data."""
        device_state = self.coordinator.get_device_state(self.device_key)
        if not device_state:
            return
        
        # Update binary sensor state - implementation depends on subclass
        self._update_binary_sensor_state_from_data(device_state)
    
    def _update_binary_sensor_state_from_data(self, device_state: Dict[str, Any]) -> None:
        """Update binary sensor state from device state data."""
        # This method should be implemented by subclasses
        pass

class TISMotionSensorEntity(TISBinarySensorEntity):
    """Motion sensor entity for TIS motion detectors."""
    
    def __init__(
        self,
        coordinator: TISDataUpdateCoordinator,
        device_key: str,
        device_name: str,
    ) -> None:
        """Initialize motion sensor entity."""
        
        motion_def = ENTITY_DEFINITIONS.get("motion_sensor", {})
        
        super().__init__(
            coordinator=coordinator,
            device_key=device_key,
            entity_key="motion",
            entity_name=f"{device_name} Motion",
            device_class=BinarySensorDeviceClass.MOTION,
            icon_on="mdi:motion-sensor",
            icon_off="mdi:motion-sensor-off"
        )
    
    def _update_binary_sensor_state_from_data(self, device_state: Dict[str, Any]) -> None:
        """Update motion sensor state from device state data."""
        # Check for motion state
        motion = device_state.get("motion")
        if motion is not None:
            self._is_on = bool(motion)
        
        # Check for generic binary state
        elif "state" in device_state:
            state = device_state["state"]
            if state in ["detected", "on", True, 1]:
                self._is_on = True
            elif state in ["clear", "off", False, 0]:
                self._is_on = False
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional motion sensor attributes."""
        attrs = super().extra_state_attributes
        
        device_state = self.coordinator.get_device_state(self.device_key)
        if device_state:
            # Add last motion time if available
            last_motion = device_state.get("last_motion")
            if last_motion:
                attrs["last_motion"] = last_motion
            
            # Add motion sensitivity if available
            sensitivity = device_state.get("sensitivity")
            if sensitivity is not None:
                attrs["sensitivity"] = sensitivity
        
        return attrs

class TISDoorWindowSensorEntity(TISBinarySensorEntity):
    """Door/window sensor entity for TIS contact sensors."""
    
    def __init__(
        self,
        coordinator: TISDataUpdateCoordinator,
        device_key: str,
        device_name: str,
    ) -> None:
        """Initialize door/window sensor entity."""
        
        door_def = ENTITY_DEFINITIONS.get("door_window_sensor", {})
        
        super().__init__(
            coordinator=coordinator,
            device_key=device_key,
            entity_key="contact",
            entity_name=f"{device_name} Contact",
            device_class=BinarySensorDeviceClass.DOOR,
            icon_on="mdi:door-open",
            icon_off="mdi:door-closed"
        )
    
    def _update_binary_sensor_state_from_data(self, device_state: Dict[str, Any]) -> None:
        """Update door/window sensor state from device state data."""
        # Check for contact/door state
        contact = device_state.get("contact")
        if contact is not None:
            self._is_on = bool(contact)  # True = open, False = closed
        
        # Check for door state
        elif "door" in device_state:
            door_state = device_state["door"]
            if door_state in ["open", "opened", True, 1]:
                self._is_on = True
            elif door_state in ["closed", False, 0]:
                self._is_on = False
        
        # Check for generic state
        elif "state" in device_state:
            state = device_state["state"]
            if state in ["open", "opened", "on", True, 1]:
                self._is_on = True
            elif state in ["closed", "off", False, 0]:
                self._is_on = False
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional door/window sensor attributes."""
        attrs = super().extra_state_attributes
        attrs["contact_state"] = "open" if self._is_on else "closed"
        
        device_state = self.coordinator.get_device_state(self.device_key)
        if device_state:
            # Add last opened/closed time if available
            last_changed = device_state.get("last_changed")
            if last_changed:
                attrs["last_changed"] = last_changed
        
        return attrs

class TISSmokeDetectorEntity(TISBinarySensorEntity):
    """Smoke detector entity for TIS smoke sensors."""
    
    def __init__(
        self,
        coordinator: TISDataUpdateCoordinator,
        device_key: str,
        device_name: str,
    ) -> None:
        """Initialize smoke detector entity."""
        
        smoke_def = ENTITY_DEFINITIONS.get("smoke_detector", {})
        
        super().__init__(
            coordinator=coordinator,
            device_key=device_key,
            entity_key="smoke",
            entity_name=f"{device_name} Smoke",
            device_class=BinarySensorDeviceClass.SMOKE,
            icon_on="mdi:smoke-detector-alert",
            icon_off="mdi:smoke-detector"
        )
    
    def _update_binary_sensor_state_from_data(self, device_state: Dict[str, Any]) -> None:
        """Update smoke detector state from device state data."""
        # Check for smoke state
        smoke = device_state.get("smoke")
        if smoke is not None:
            self._is_on = bool(smoke)  # True = smoke detected, False = clear
        
        # Check for alarm state
        elif "alarm" in device_state:
            alarm_state = device_state["alarm"]
            if alarm_state in ["smoke", "fire", "alarm", True, 1]:
                self._is_on = True
            elif alarm_state in ["clear", "normal", False, 0]:
                self._is_on = False
        
        # Check for generic state
        elif "state" in device_state:
            state = device_state["state"]
            if state in ["detected", "alarm", "on", True, 1]:
                self._is_on = True
            elif state in ["clear", "normal", "off", False, 0]:
                self._is_on = False
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional smoke detector attributes."""
        attrs = super().extra_state_attributes
        
        device_state = self.coordinator.get_device_state(self.device_key)
        if device_state:
            # Add smoke level if available
            smoke_level = device_state.get("smoke_level")
            if smoke_level is not None:
                attrs["smoke_level"] = smoke_level
            
            # Add battery level for battery-powered detectors
            battery = device_state.get("battery_level")
            if battery is not None:
                attrs["battery_level"] = battery
            
            # Add last alarm time
            last_alarm = device_state.get("last_alarm")
            if last_alarm:
                attrs["last_alarm"] = last_alarm
        
        return attrs

class TISGasDetectorEntity(TISBinarySensorEntity):
    """Gas detector entity for TIS gas sensors."""
    
    def __init__(
        self,
        coordinator: TISDataUpdateCoordinator,
        device_key: str,
        device_name: str,
    ) -> None:
        """Initialize gas detector entity."""
        
        gas_def = ENTITY_DEFINITIONS.get("gas_detector", {})
        
        super().__init__(
            coordinator=coordinator,
            device_key=device_key,
            entity_key="gas",
            entity_name=f"{device_name} Gas",
            device_class=BinarySensorDeviceClass.GAS,
            icon_on="mdi:gas-cylinder",
            icon_off="mdi:gas-cylinder-outline"
        )
    
    def _update_binary_sensor_state_from_data(self, device_state: Dict[str, Any]) -> None:
        """Update gas detector state from device state data."""
        # Check for gas state
        gas = device_state.get("gas")
        if gas is not None:
            self._is_on = bool(gas)  # True = gas detected, False = clear
        
        # Check for alarm state
        elif "alarm" in device_state:
            alarm_state = device_state["alarm"]
            if alarm_state in ["gas", "leak", "alarm", True, 1]:
                self._is_on = True
            elif alarm_state in ["clear", "normal", False, 0]:
                self._is_on = False
        
        # Check for generic state
        elif "state" in device_state:
            state = device_state["state"]
            if state in ["detected", "alarm", "on", True, 1]:
                self._is_on = True
            elif state in ["clear", "normal", "off", False, 0]:
                self._is_on = False
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional gas detector attributes."""
        attrs = super().extra_state_attributes
        
        device_state = self.coordinator.get_device_state(self.device_key)
        if device_state:
            # Add gas concentration if available
            gas_level = device_state.get("gas_level")
            if gas_level is not None:
                attrs["gas_level"] = gas_level
                attrs["gas_level_unit"] = "ppm"
            
            # Add gas type if specified
            gas_type = device_state.get("gas_type")
            if gas_type:
                attrs["gas_type"] = gas_type
            
            # Add last alarm time
            last_alarm = device_state.get("last_alarm")
            if last_alarm:
                attrs["last_alarm"] = last_alarm
        
        return attrs

class TISSecuritySensorEntity(TISBinarySensorEntity):
    """Security sensor entity for TIS security/alarm devices."""
    
    def __init__(
        self,
        coordinator: TISDataUpdateCoordinator,
        device_key: str,
        device_name: str,
        sensor_index: int = 0,
    ) -> None:
        """Initialize security sensor entity."""
        
        entity_key = f"security_{sensor_index}"
        entity_name = f"{device_name} Security"
        if sensor_index > 0:
            entity_name += f" {sensor_index + 1}"
        
        super().__init__(
            coordinator=coordinator,
            device_key=device_key,
            entity_key=entity_key,
            entity_name=entity_name,
            device_class=BinarySensorDeviceClass.SAFETY,
            icon_on="mdi:shield-alert",
            icon_off="mdi:shield-check"
        )
        
        self.sensor_index = sensor_index
    
    def _update_binary_sensor_state_from_data(self, device_state: Dict[str, Any]) -> None:
        """Update security sensor state from device state data."""
        # Check for indexed security state
        security_state = device_state.get(f"security_{self.sensor_index}")
        if security_state is not None:
            self._is_on = bool(security_state)
        
        # Check for alarm state
        elif "alarm" in device_state:
            alarm_state = device_state["alarm"]
            if alarm_state in ["triggered", "alarm", "breach", True, 1]:
                self._is_on = True
            elif alarm_state in ["disarmed", "normal", "secure", False, 0]:
                self._is_on = False
        
        # Check for security status
        elif "security_status" in device_state:
            status = device_state["security_status"]
            if status in ["armed", "triggered", "alarm"]:
                self._is_on = True
            elif status in ["disarmed", "normal"]:
                self._is_on = False
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional security sensor attributes."""
        attrs = super().extra_state_attributes
        attrs["sensor_index"] = self.sensor_index
        
        device_state = self.coordinator.get_device_state(self.device_key)
        if device_state:
            # Add security zone if available
            zone = device_state.get("zone")
            if zone is not None:
                attrs["zone"] = zone
            
            # Add last triggered time
            last_triggered = device_state.get("last_triggered")
            if last_triggered:
                attrs["last_triggered"] = last_triggered
        
        return attrs

class TISGenericBinarySensorEntity(TISBinarySensorEntity):
    """Generic binary sensor entity for unknown TIS binary sensor devices."""
    
    def __init__(
        self,
        coordinator: TISDataUpdateCoordinator,
        device_key: str,
        device_name: str,
        sensor_index: int = 0,
    ) -> None:
        """Initialize generic binary sensor entity."""
        
        entity_key = f"binary_sensor_{sensor_index}"
        entity_name = f"{device_name} Binary Sensor"
        if sensor_index > 0:
            entity_name += f" {sensor_index + 1}"
        
        super().__init__(
            coordinator=coordinator,
            device_key=device_key,
            entity_key=entity_key,
            entity_name=entity_name,
            icon_on="mdi:checkbox-marked-circle",
            icon_off="mdi:checkbox-blank-circle-outline"
        )
        
        self.sensor_index = sensor_index
    
    def _update_binary_sensor_state_from_data(self, device_state: Dict[str, Any]) -> None:
        """Update generic binary sensor state from device state data."""
        # Try to find binary sensor data in various formats
        # First check for indexed sensor data
        sensor_data = device_state.get(f"binary_sensor_{self.sensor_index}")
        if sensor_data is not None:
            self._is_on = bool(sensor_data)
            return
        
        # Check for array of binary sensor values
        sensors = device_state.get("binary_sensors")
        if isinstance(sensors, list) and len(sensors) > self.sensor_index:
            self._is_on = bool(sensors[self.sensor_index])
            return
        
        # Check for generic state (only for first sensor)
        if self.sensor_index == 0:
            state = device_state.get("state")
            if state is not None:
                if state in ["on", "active", "detected", True, 1]:
                    self._is_on = True
                elif state in ["off", "inactive", "clear", False, 0]:
                    self._is_on = False
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional generic binary sensor attributes."""
        attrs = super().extra_state_attributes
        attrs["sensor_index"] = self.sensor_index
        
        # Add raw device state for debugging
        device_state = self.coordinator.get_device_state(self.device_key)
        if device_state:
            attrs["raw_data"] = str(device_state)
        
        return attrs

# Specialized binary sensor entities for specific use cases

class TISConnectionStatusEntity(TISBinarySensorEntity):
    """Connection status binary sensor for TIS devices."""
    
    def __init__(
        self,
        coordinator: TISDataUpdateCoordinator,
        device_key: str,
        device_name: str,
    ) -> None:
        """Initialize connection status entity."""
        
        super().__init__(
            coordinator=coordinator,
            device_key=device_key,
            entity_key="connection",
            entity_name=f"{device_name} Connection",
            device_class=BinarySensorDeviceClass.CONNECTIVITY,
            icon_on="mdi:wifi",
            icon_off="mdi:wifi-off"
        )
    
    @property
    def is_on(self) -> bool:
        """Return True if device is connected."""
        return self.coordinator.is_device_online(self.device_key)
    
    def _update_binary_sensor_state_from_data(self, device_state: Dict[str, Any]) -> None:
        """Update connection status - handled by is_on property."""
        pass

class TISBatteryLowEntity(TISBinarySensorEntity):
    """Low battery binary sensor for battery-powered TIS devices."""
    
    def __init__(
        self,
        coordinator: TISDataUpdateCoordinator,
        device_key: str,
        device_name: str,
    ) -> None:
        """Initialize low battery entity."""
        
        super().__init__(
            coordinator=coordinator,
            device_key=device_key,
            entity_key="battery_low",
            entity_name=f"{device_name} Battery Low",
            device_class=BinarySensorDeviceClass.BATTERY,
            icon_on="mdi:battery-alert",
            icon_off="mdi:battery"
        )
    
    def _update_binary_sensor_state_from_data(self, device_state: Dict[str, Any]) -> None:
        """Update low battery status from device state data."""
        # Check for explicit low battery flag
        battery_low = device_state.get("battery_low")
        if battery_low is not None:
            self._is_on = bool(battery_low)
            return
        
        # Check battery level and determine if low
        battery_level = device_state.get("battery_level")
        if battery_level is not None:
            self._is_on = int(battery_level) <= 15  # Consider <= 15% as low
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional battery attributes."""
        attrs = super().extra_state_attributes
        
        device_state = self.coordinator.get_device_state(self.device_key)
        if device_state:
            battery_level = device_state.get("battery_level")
            if battery_level is not None:
                attrs["battery_level"] = battery_level
        
        return attrs
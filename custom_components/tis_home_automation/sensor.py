"""
Sensor platform for TIS Home Automation integration.
Supports all TIS sensor devices including multi-sensor health monitors.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfTemperature,
    UnitOfIlluminance,
    UnitOfSoundPressure,
    CONCENTRATION_PARTS_PER_MILLION,
    CONCENTRATION_PARTS_PER_BILLION,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    TIS_DEVICE_TYPES,
    TIS_OPCODES,
    DEVICE_CAPABILITIES,
    ENTITY_DEFINITIONS,
    HEALTH_SENSOR_MAPPING,
)
from .coordinator import TISDataUpdateCoordinator
from .entity import TISBaseEntity, TISSensorEntity, TISDeviceWrapper

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up TIS sensor entities from config entry."""
    
    # Get coordinator and devices from hass data
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    coordinator: TISDataUpdateCoordinator = entry_data["coordinator"]
    discovered_devices = entry_data["discovered_devices"]
    
    entities = []
    
    # Create sensor entities for each discovered device
    for device_key, tis_device in discovered_devices.items():
        device_wrapper = TISDeviceWrapper(tis_device, coordinator)
        device_type_name = device_wrapper.device_type_name
        
        # Check if device has sensor capabilities
        capabilities = DEVICE_CAPABILITIES.get(device_type_name, [])
        
        sensor_indices = [i for i, cap in enumerate(capabilities) if cap == "sensor"]
        
        for sensor_index in sensor_indices:
            # Create sensor entities based on device type
            sensor_entities = create_sensor_entities_for_device(
                coordinator, device_wrapper, sensor_index
            )
            entities.extend(sensor_entities)
    
    if entities:
        async_add_entities(entities, True)
        _LOGGER.info(f"Added {len(entities)} TIS sensor entities")

def create_sensor_entities_for_device(
    coordinator: TISDataUpdateCoordinator,
    device_wrapper: TISDeviceWrapper,
    sensor_index: int = 0
) -> List[TISSensorEntity]:
    """Create sensor entities for a TIS device based on its type."""
    
    device_type_name = device_wrapper.device_type_name
    device_key = device_wrapper.device_key
    device_name = device_wrapper.tis_device.name
    
    entities = []
    
    # Health sensor (multi-sensor device)
    if "health_sensor" in device_type_name:
        for sensor_type, sensor_config in HEALTH_SENSOR_MAPPING.items():
            entity = TISHealthSensorEntity(
                coordinator=coordinator,
                device_key=device_key,
                sensor_key=sensor_type,
                sensor_name=f"{device_name} {sensor_config['name']}",
                icon=sensor_config.get("icon"),
                device_class=sensor_config.get("device_class"),
                unit_of_measurement=sensor_config.get("unit"),
                state_class=sensor_config.get("state_class")
            )
            entities.append(entity)
            _LOGGER.debug(f"Added TIS health sensor entity: {entity.name}")
    
    # Temperature sensor
    elif "temperature_sensor" in device_type_name:
        entity = TISTemperatureSensorEntity(
            coordinator=coordinator,
            device_key=device_key,
            device_name=device_name
        )
        entities.append(entity)
    
    # Humidity sensor
    elif "humidity_sensor" in device_type_name:
        entity = TISHumiditySensorEntity(
            coordinator=coordinator,
            device_key=device_key,
            device_name=device_name
        )
        entities.append(entity)
    
    # Light sensor
    elif "light_sensor" in device_type_name:
        entity = TISLightSensorEntity(
            coordinator=coordinator,
            device_key=device_key,
            device_name=device_name
        )
        entities.append(entity)
    
    # Noise sensor
    elif "noise_sensor" in device_type_name:
        entity = TISNoiseSensorEntity(
            coordinator=coordinator,
            device_key=device_key,
            device_name=device_name
        )
        entities.append(entity)
    
    # Air quality sensor
    elif "air_quality_sensor" in device_type_name:
        # Air quality sensors might have multiple readings
        entity = TISAirQualitySensorEntity(
            coordinator=coordinator,
            device_key=device_key,
            device_name=device_name
        )
        entities.append(entity)
    
    # Generic sensor fallback
    else:
        entity = TISGenericSensorEntity(
            coordinator=coordinator,
            device_key=device_key,
            device_name=device_name,
            sensor_index=sensor_index
        )
        entities.append(entity)
    
    return entities

class TISHealthSensorEntity(TISSensorEntity):
    """Individual sensor entity for health sensor sub-sensors."""
    
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
        """Initialize health sensor entity."""
        
        super().__init__(
            coordinator=coordinator,
            device_key=device_key,
            sensor_key=sensor_key,
            sensor_name=sensor_name,
            icon=icon,
            device_class=device_class,
            unit_of_measurement=unit_of_measurement,
            state_class=state_class
        )
    
    @property
    def state(self) -> Any:
        """Return the state of the health sensor sub-sensor."""
        device_state = self.coordinator.get_device_state(self.device_key)
        if not device_state:
            return None
        
        # Health sensor data is stored in 'sensors' dict
        sensors_data = device_state.get("sensors", {})
        if isinstance(sensors_data, dict):
            return sensors_data.get(self.sensor_key)
        
        return None
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional attributes for health sensor."""
        attrs = super().extra_state_attributes
        
        # Add all health sensor readings as attributes
        device_state = self.coordinator.get_device_state(self.device_key)
        if device_state and "sensors" in device_state:
            sensors_data = device_state["sensors"]
            if isinstance(sensors_data, dict):
                attrs.update({
                    f"health_sensor_{key}": value 
                    for key, value in sensors_data.items()
                    if key != self.sensor_key  # Don't duplicate main state
                })
        
        return attrs

class TISTemperatureSensorEntity(TISSensorEntity):
    """Temperature sensor entity for TIS devices."""
    
    def __init__(
        self,
        coordinator: TISDataUpdateCoordinator,
        device_key: str,
        device_name: str,
    ) -> None:
        """Initialize temperature sensor entity."""
        
        temp_def = ENTITY_DEFINITIONS.get("temperature_sensor", {})
        
        super().__init__(
            coordinator=coordinator,
            device_key=device_key,
            sensor_key="temperature",
            sensor_name=f"{device_name} Temperature",
            icon=temp_def.get("icon"),
            device_class=temp_def.get("device_class"),
            unit_of_measurement=temp_def.get("unit", UnitOfTemperature.CELSIUS),
            state_class=SensorStateClass.MEASUREMENT
        )
    
    @property
    def state(self) -> Optional[float]:
        """Return temperature value."""
        device_state = self.coordinator.get_device_state(self.device_key)
        if not device_state:
            return None
        
        # Check for temperature in various possible locations
        temp = device_state.get("temperature")
        if temp is not None:
            return float(temp)
        
        # Check in sensors dict (for multi-sensor devices)
        sensors_data = device_state.get("sensors", {})
        if isinstance(sensors_data, dict):
            temp = sensors_data.get("temperature")
            if temp is not None:
                return float(temp)
        
        return None

class TISHumiditySensorEntity(TISSensorEntity):
    """Humidity sensor entity for TIS devices."""
    
    def __init__(
        self,
        coordinator: TISDataUpdateCoordinator,
        device_key: str,
        device_name: str,
    ) -> None:
        """Initialize humidity sensor entity."""
        
        humidity_def = ENTITY_DEFINITIONS.get("humidity_sensor", {})
        
        super().__init__(
            coordinator=coordinator,
            device_key=device_key,
            sensor_key="humidity",
            sensor_name=f"{device_name} Humidity",
            icon=humidity_def.get("icon"),
            device_class=humidity_def.get("device_class"),
            unit_of_measurement=humidity_def.get("unit", PERCENTAGE),
            state_class=SensorStateClass.MEASUREMENT
        )
    
    @property
    def state(self) -> Optional[float]:
        """Return humidity value."""
        device_state = self.coordinator.get_device_state(self.device_key)
        if not device_state:
            return None
        
        # Check for humidity in various possible locations
        humidity = device_state.get("humidity")
        if humidity is not None:
            return float(humidity)
        
        # Check in sensors dict (for multi-sensor devices)
        sensors_data = device_state.get("sensors", {})
        if isinstance(sensors_data, dict):
            humidity = sensors_data.get("humidity")
            if humidity is not None:
                return float(humidity)
        
        return None

class TISLightSensorEntity(TISSensorEntity):
    """Light sensor entity for TIS devices."""
    
    def __init__(
        self,
        coordinator: TISDataUpdateCoordinator,
        device_key: str,
        device_name: str,
    ) -> None:
        """Initialize light sensor entity."""
        
        light_def = ENTITY_DEFINITIONS.get("light_sensor", {})
        
        super().__init__(
            coordinator=coordinator,
            device_key=device_key,
            sensor_key="lux",
            sensor_name=f"{device_name} Illuminance",
            icon=light_def.get("icon"),
            device_class=light_def.get("device_class"),
            unit_of_measurement=light_def.get("unit", UnitOfIlluminance.LUX),
            state_class=SensorStateClass.MEASUREMENT
        )
    
    @property
    def state(self) -> Optional[int]:
        """Return illuminance value."""
        device_state = self.coordinator.get_device_state(self.device_key)
        if not device_state:
            return None
        
        # Check for lux in various possible locations
        lux = device_state.get("lux")
        if lux is not None:
            return int(lux)
        
        # Check in sensors dict
        sensors_data = device_state.get("sensors", {})
        if isinstance(sensors_data, dict):
            lux = sensors_data.get("lux")
            if lux is not None:
                return int(lux)
        
        return None

class TISNoiseSensorEntity(TISSensorEntity):
    """Noise sensor entity for TIS devices."""
    
    def __init__(
        self,
        coordinator: TISDataUpdateCoordinator,
        device_key: str,
        device_name: str,
    ) -> None:
        """Initialize noise sensor entity."""
        
        noise_def = ENTITY_DEFINITIONS.get("noise_sensor", {})
        
        super().__init__(
            coordinator=coordinator,
            device_key=device_key,
            sensor_key="noise",
            sensor_name=f"{device_name} Noise Level",
            icon=noise_def.get("icon"),
            device_class=noise_def.get("device_class"),
            unit_of_measurement=noise_def.get("unit", UnitOfSoundPressure.DECIBEL),
            state_class=SensorStateClass.MEASUREMENT
        )
    
    @property
    def state(self) -> Optional[int]:
        """Return noise level value."""
        device_state = self.coordinator.get_device_state(self.device_key)
        if not device_state:
            return None
        
        # Check for noise in various possible locations
        noise = device_state.get("noise")
        if noise is not None:
            return int(noise)
        
        # Check in sensors dict
        sensors_data = device_state.get("sensors", {})
        if isinstance(sensors_data, dict):
            noise = sensors_data.get("noise")
            if noise is not None:
                return int(noise)
        
        return None

class TISAirQualitySensorEntity(TISSensorEntity):
    """Air quality sensor entity for TIS devices."""
    
    def __init__(
        self,
        coordinator: TISDataUpdateCoordinator,
        device_key: str,
        device_name: str,
    ) -> None:
        """Initialize air quality sensor entity."""
        
        air_def = ENTITY_DEFINITIONS.get("air_quality_sensor", {})
        
        super().__init__(
            coordinator=coordinator,
            device_key=device_key,
            sensor_key="aqi",
            sensor_name=f"{device_name} Air Quality",
            icon=air_def.get("icon"),
            device_class=air_def.get("device_class"),
            state_class=SensorStateClass.MEASUREMENT
        )
    
    @property
    def state(self) -> Optional[int]:
        """Return air quality index."""
        device_state = self.coordinator.get_device_state(self.device_key)
        if not device_state:
            return None
        
        # Calculate AQI from available data or use direct AQI value
        aqi = device_state.get("aqi")
        if aqi is not None:
            return int(aqi)
        
        # Calculate AQI from eCO2 and TVOC if available
        sensors_data = device_state.get("sensors", {})
        if isinstance(sensors_data, dict):
            eco2 = sensors_data.get("eco2")
            tvoc = sensors_data.get("tvoc")
            
            if eco2 is not None and tvoc is not None:
                # Simple AQI calculation based on eCO2 and TVOC
                # This is a simplified version - real AQI calculation is more complex
                eco2_score = min(100, max(0, (eco2 - 400) / 10))  # 400ppm baseline
                tvoc_score = min(100, max(0, tvoc / 10))  # Simple TVOC scoring
                
                # Combine scores (weighted average)
                aqi = int((eco2_score * 0.6 + tvoc_score * 0.4))
                return aqi
        
        return None
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional air quality attributes."""
        attrs = super().extra_state_attributes
        
        device_state = self.coordinator.get_device_state(self.device_key)
        if device_state and "sensors" in device_state:
            sensors_data = device_state["sensors"]
            if isinstance(sensors_data, dict):
                # Add individual air quality components
                eco2 = sensors_data.get("eco2")
                if eco2 is not None:
                    attrs["eco2"] = eco2
                    attrs["eco2_unit"] = "ppm"
                
                tvoc = sensors_data.get("tvoc")
                if tvoc is not None:
                    attrs["tvoc"] = tvoc
                    attrs["tvoc_unit"] = "ppb"
                
                # Add air quality rating
                aqi = self.state
                if aqi is not None:
                    if aqi <= 20:
                        attrs["air_quality_rating"] = "Excellent"
                    elif aqi <= 40:
                        attrs["air_quality_rating"] = "Good"
                    elif aqi <= 60:
                        attrs["air_quality_rating"] = "Moderate"
                    elif aqi <= 80:
                        attrs["air_quality_rating"] = "Poor"
                    else:
                        attrs["air_quality_rating"] = "Unhealthy"
        
        return attrs

class TISGenericSensorEntity(TISSensorEntity):
    """Generic sensor entity for unknown TIS sensor devices."""
    
    def __init__(
        self,
        coordinator: TISDataUpdateCoordinator,
        device_key: str,
        device_name: str,
        sensor_index: int = 0,
    ) -> None:
        """Initialize generic sensor entity."""
        
        sensor_key = f"sensor_{sensor_index}"
        entity_name = f"{device_name} Sensor"
        if sensor_index > 0:
            entity_name += f" {sensor_index + 1}"
        
        super().__init__(
            coordinator=coordinator,
            device_key=device_key,
            sensor_key=sensor_key,
            sensor_name=entity_name,
            icon="mdi:eye",
            state_class=SensorStateClass.MEASUREMENT
        )
        
        self.sensor_index = sensor_index
    
    @property
    def state(self) -> Any:
        """Return generic sensor value."""
        device_state = self.coordinator.get_device_state(self.device_key)
        if not device_state:
            return None
        
        # Try to find sensor data in various formats
        # First check for indexed sensor data
        sensor_data = device_state.get(f"sensor_{self.sensor_index}")
        if sensor_data is not None:
            return sensor_data
        
        # Check for array of sensor values
        sensors = device_state.get("sensors")
        if isinstance(sensors, list) and len(sensors) > self.sensor_index:
            return sensors[self.sensor_index]
        
        # Check for generic value
        if self.sensor_index == 0:
            return device_state.get("value")
        
        return None
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional generic sensor attributes."""
        attrs = super().extra_state_attributes
        attrs["sensor_index"] = self.sensor_index
        
        # Add raw device state for debugging
        device_state = self.coordinator.get_device_state(self.device_key)
        if device_state:
            attrs["raw_data"] = str(device_state)
        
        return attrs

# Specialized sensor entities for specific TIS devices

class TISMotionDetectedSensorEntity(TISSensorEntity):
    """Motion detection timestamp sensor."""
    
    def __init__(
        self,
        coordinator: TISDataUpdateCoordinator,
        device_key: str,
        device_name: str,
    ) -> None:
        """Initialize motion detected sensor."""
        
        super().__init__(
            coordinator=coordinator,
            device_key=device_key,
            sensor_key="last_motion",
            sensor_name=f"{device_name} Last Motion",
            icon="mdi:clock-outline",
            device_class=SensorDeviceClass.TIMESTAMP
        )
    
    @property
    def state(self) -> Optional[str]:
        """Return last motion detection time."""
        device_state = self.coordinator.get_device_state(self.device_key)
        if not device_state:
            return None
        
        return device_state.get("last_motion")

class TISBatteryLevelSensorEntity(TISSensorEntity):
    """Battery level sensor for battery-powered TIS devices."""
    
    def __init__(
        self,
        coordinator: TISDataUpdateCoordinator,
        device_key: str,
        device_name: str,
    ) -> None:
        """Initialize battery level sensor."""
        
        super().__init__(
            coordinator=coordinator,
            device_key=device_key,
            sensor_key="battery_level",
            sensor_name=f"{device_name} Battery",
            icon="mdi:battery",
            device_class=SensorDeviceClass.BATTERY,
            unit_of_measurement=PERCENTAGE,
            state_class=SensorStateClass.MEASUREMENT
        )
    
    @property
    def state(self) -> Optional[int]:
        """Return battery level percentage."""
        device_state = self.coordinator.get_device_state(self.device_key)
        if not device_state:
            return None
        
        battery = device_state.get("battery_level")
        if battery is not None:
            return int(battery)
        
        return None
    
    @property
    def icon(self) -> str:
        """Return battery icon based on level."""
        battery_level = self.state
        if battery_level is None:
            return "mdi:battery-unknown"
        
        if battery_level <= 10:
            return "mdi:battery-10"
        elif battery_level <= 20:
            return "mdi:battery-20"
        elif battery_level <= 30:
            return "mdi:battery-30"
        elif battery_level <= 40:
            return "mdi:battery-40"
        elif battery_level <= 50:
            return "mdi:battery-50"
        elif battery_level <= 60:
            return "mdi:battery-60"
        elif battery_level <= 70:
            return "mdi:battery-70"
        elif battery_level <= 80:
            return "mdi:battery-80"
        elif battery_level <= 90:
            return "mdi:battery-90"
        else:
            return "mdi:battery"

class TISSignalStrengthSensorEntity(TISSensorEntity):
    """Signal strength sensor for TIS devices."""
    
    def __init__(
        self,
        coordinator: TISDataUpdateCoordinator,
        device_key: str,
        device_name: str,
    ) -> None:
        """Initialize signal strength sensor."""
        
        super().__init__(
            coordinator=coordinator,
            device_key=device_key,
            sensor_key="signal_strength",
            sensor_name=f"{device_name} Signal Strength",
            icon="mdi:wifi",
            device_class=SensorDeviceClass.SIGNAL_STRENGTH,
            unit_of_measurement="dBm",
            state_class=SensorStateClass.MEASUREMENT
        )
    
    @property
    def state(self) -> Optional[int]:
        """Return signal strength in dBm."""
        device_state = self.coordinator.get_device_state(self.device_key)
        if not device_state:
            return None
        
        signal = device_state.get("signal_strength")
        if signal is not None:
            return int(signal)
        
        return None
    
    @property
    def icon(self) -> str:
        """Return signal strength icon based on level."""
        signal_level = self.state
        if signal_level is None:
            return "mdi:wifi-off"
        
        # dBm to signal strength mapping (typical WiFi levels)
        if signal_level >= -30:
            return "mdi:wifi-strength-4"
        elif signal_level >= -50:
            return "mdi:wifi-strength-3"
        elif signal_level >= -70:
            return "mdi:wifi-strength-2"
        elif signal_level >= -90:
            return "mdi:wifi-strength-1"
        else:
            return "mdi:wifi-strength-outline"
"""
Climate platform for TIS Home Automation integration.
Supports TIS AC controllers, thermostats, and heating devices.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
    HVACAction,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    TIS_DEVICE_TYPES,
    TIS_OPCODES,
    DEVICE_CAPABILITIES,
    ENTITY_DEFINITIONS,
    AC_MODES,
    AC_FAN_SPEEDS,
)
from .coordinator import TISDataUpdateCoordinator
from .entity import TISBaseEntity, TISDeviceWrapper

_LOGGER = logging.getLogger(__name__)

# Climate device constants
MIN_TEMP = 16  # Minimum temperature in Celsius
MAX_TEMP = 30  # Maximum temperature in Celsius
DEFAULT_TEMP = 24  # Default temperature
TEMP_STEP = 1.0  # Temperature step

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up TIS climate entities from config entry."""
    
    # Get coordinator and devices from hass data
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    coordinator: TISDataUpdateCoordinator = entry_data["coordinator"]
    discovered_devices = entry_data["discovered_devices"]
    
    entities = []
    
    # Create climate entities for each discovered device
    for device_key, tis_device in discovered_devices.items():
        device_wrapper = TISDeviceWrapper(tis_device, coordinator)
        device_type_name = device_wrapper.device_type_name
        
        # Check if device has climate capabilities
        capabilities = DEVICE_CAPABILITIES.get(device_type_name, [])
        
        climate_indices = [i for i, cap in enumerate(capabilities) if cap == "climate"]
        
        for climate_index in climate_indices:
            # Create climate entity based on device type
            entity = create_climate_entity_for_device(
                coordinator, device_wrapper, climate_index
            )
            if entity:
                entities.append(entity)
                _LOGGER.debug(f"Added TIS climate entity: {entity.name}")
    
    if entities:
        async_add_entities(entities, True)
        _LOGGER.info(f"Added {len(entities)} TIS climate entities")

def create_climate_entity_for_device(
    coordinator: TISDataUpdateCoordinator,
    device_wrapper: TISDeviceWrapper,
    climate_index: int = 0
) -> Optional[TISClimateEntity]:
    """Create climate entity for a TIS device based on its type."""
    
    device_type_name = device_wrapper.device_type_name
    device_key = device_wrapper.device_key
    device_name = device_wrapper.tis_device.name
    
    # AC controller
    if "ac_controller" in device_type_name:
        return TISACControllerEntity(
            coordinator=coordinator,
            device_key=device_key,
            device_name=device_name
        )
    
    # Thermostat
    elif "thermostat" in device_type_name:
        return TISThermostatEntity(
            coordinator=coordinator,
            device_key=device_key,
            device_name=device_name
        )
    
    # Floor heating controller
    elif "floor_heating" in device_type_name:
        return TISFloorHeatingEntity(
            coordinator=coordinator,
            device_key=device_key,
            device_name=device_name
        )
    
    # Generic climate controller
    else:
        return TISGenericClimateEntity(
            coordinator=coordinator,
            device_key=device_key,
            device_name=device_name,
            climate_index=climate_index
        )

class TISClimateEntity(TISBaseEntity, ClimateEntity):
    """Base class for TIS climate entities."""
    
    def __init__(
        self,
        coordinator: TISDataUpdateCoordinator,
        device_key: str,
        entity_key: str,
        entity_name: str,
        hvac_modes: List[HVACMode] = None,
        supported_features: ClimateEntityFeature = ClimateEntityFeature(0),
    ) -> None:
        """Initialize TIS climate entity."""
        
        # Get climate icon from entity definitions
        climate_def = ENTITY_DEFINITIONS.get("climate", {})
        
        super().__init__(
            coordinator=coordinator,
            device_key=device_key,
            entity_key=entity_key,
            entity_name=entity_name,
            entity_type="climate",
            icon=climate_def.get("icon"),
            device_class=climate_def.get("device_class")
        )
        
        # Climate state
        self._hvac_mode = HVACMode.OFF
        self._hvac_action = HVACAction.OFF
        self._current_temperature = None
        self._target_temperature = DEFAULT_TEMP
        self._current_humidity = None
        self._target_humidity = None
        self._fan_mode = "auto"
        self._preset_mode = None
        
        # Set supported features and modes
        self._attr_hvac_modes = hvac_modes or [HVACMode.OFF, HVACMode.AUTO]
        self._attr_supported_features = supported_features
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_min_temp = MIN_TEMP
        self._attr_max_temp = MAX_TEMP
        self._attr_target_temperature_step = TEMP_STEP
    
    @property
    def hvac_mode(self) -> HVACMode:
        """Return current HVAC mode."""
        return self._hvac_mode
    
    @property
    def hvac_action(self) -> Optional[HVACAction]:
        """Return current HVAC action."""
        return self._hvac_action
    
    @property
    def current_temperature(self) -> Optional[float]:
        """Return current temperature."""
        return self._current_temperature
    
    @property
    def target_temperature(self) -> Optional[float]:
        """Return target temperature."""
        return self._target_temperature
    
    @property
    def current_humidity(self) -> Optional[int]:
        """Return current humidity."""
        return self._current_humidity
    
    @property
    def target_humidity(self) -> Optional[int]:
        """Return target humidity."""
        return self._target_humidity
    
    @property
    def fan_mode(self) -> Optional[str]:
        """Return current fan mode."""
        return self._fan_mode
    
    @property
    def preset_mode(self) -> Optional[str]:
        """Return current preset mode."""
        return self._preset_mode
    
    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target HVAC mode."""
        success = await self._send_hvac_mode_command(hvac_mode)
        if success:
            self._hvac_mode = hvac_mode
            if hvac_mode == HVACMode.OFF:
                self._hvac_action = HVACAction.OFF
            self.async_write_ha_state()
    
    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        
        success = await self._send_temperature_command(temperature)
        if success:
            self._target_temperature = temperature
            self.async_write_ha_state()
    
    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set new target fan mode."""
        success = await self._send_fan_mode_command(fan_mode)
        if success:
            self._fan_mode = fan_mode
            self.async_write_ha_state()
    
    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        success = await self._send_preset_mode_command(preset_mode)
        if success:
            self._preset_mode = preset_mode
            self.async_write_ha_state()
    
    async def _send_hvac_mode_command(self, hvac_mode: HVACMode) -> bool:
        """Send HVAC mode command to device."""
        # This method should be implemented by subclasses
        raise NotImplementedError()
    
    async def _send_temperature_command(self, temperature: float) -> bool:
        """Send temperature command to device."""
        # This method should be implemented by subclasses
        raise NotImplementedError()
    
    async def _send_fan_mode_command(self, fan_mode: str) -> bool:
        """Send fan mode command to device."""
        # This method should be implemented by subclasses
        raise NotImplementedError()
    
    async def _send_preset_mode_command(self, preset_mode: str) -> bool:
        """Send preset mode command to device."""
        # This method should be implemented by subclasses
        raise NotImplementedError()
    
    def _update_from_coordinator_data(self) -> None:
        """Update climate state from coordinator data."""
        device_state = self.coordinator.get_device_state(self.device_key)
        if not device_state:
            return
        
        # Update climate state - implementation depends on subclass
        self._update_climate_state_from_data(device_state)
    
    def _update_climate_state_from_data(self, device_state: Dict[str, Any]) -> None:
        """Update climate state from device state data."""
        # This method should be implemented by subclasses
        pass

class TISACControllerEntity(TISClimateEntity):
    """AC controller entity for TIS AC devices."""
    
    def __init__(
        self,
        coordinator: TISDataUpdateCoordinator,
        device_key: str,
        device_name: str,
    ) -> None:
        """Initialize AC controller entity."""
        
        super().__init__(
            coordinator=coordinator,
            device_key=device_key,
            entity_key="ac",
            entity_name=f"{device_name} AC",
            hvac_modes=[HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT, HVACMode.FAN_ONLY, HVACMode.AUTO],
            supported_features=(
                ClimateEntityFeature.TARGET_TEMPERATURE |
                ClimateEntityFeature.FAN_MODE |
                ClimateEntityFeature.PRESET_MODE |
                ClimateEntityFeature.TURN_ON |
                ClimateEntityFeature.TURN_OFF
            )
        )
        
        # AC-specific settings
        self._attr_fan_modes = ["auto", "low", "medium", "high"]
        self._attr_preset_modes = ["none", "eco", "turbo", "sleep"]
        self._attr_min_temp = 16
        self._attr_max_temp = 30
    
    async def _send_hvac_mode_command(self, hvac_mode: HVACMode) -> bool:
        """Send AC HVAC mode command."""
        try:
            if hvac_mode == HVACMode.OFF:
                op_code = TIS_OPCODES["AC_POWER_OFF"]
                additional_data = []
            else:
                op_code = TIS_OPCODES["AC_POWER_ON"]
                
                # Map HVAC mode to TIS AC mode
                if hvac_mode == HVACMode.COOL:
                    tis_mode = 0  # Cool
                elif hvac_mode == HVACMode.HEAT:
                    tis_mode = 1  # Heat
                elif hvac_mode == HVACMode.FAN_ONLY:
                    tis_mode = 2  # Fan
                elif hvac_mode == HVACMode.AUTO:
                    tis_mode = 3  # Auto
                else:
                    tis_mode = 3  # Default to auto
                
                additional_data = [tis_mode]
            
            success = await self.async_send_command(op_code, additional_data)
            
            if success:
                _LOGGER.debug(f"AC {self.entity_id} HVAC mode set to {hvac_mode}")
            else:
                _LOGGER.warning(f"Failed to set AC {self.entity_id} HVAC mode to {hvac_mode}")
            
            return success
            
        except Exception as e:
            _LOGGER.error(f"Error setting AC HVAC mode for {self.entity_id}: {e}")
            return False
    
    async def _send_temperature_command(self, temperature: float) -> bool:
        """Send AC temperature command."""
        try:
            # Send temperature setting command
            op_code = TIS_OPCODES["AC_SET_TEMPERATURE"]
            temp_value = int(temperature)  # TIS uses integer temperature
            additional_data = [temp_value]
            
            success = await self.async_send_command(op_code, additional_data)
            
            if success:
                _LOGGER.debug(f"AC {self.entity_id} temperature set to {temperature}°C")
            else:
                _LOGGER.warning(f"Failed to set AC {self.entity_id} temperature to {temperature}°C")
            
            return success
            
        except Exception as e:
            _LOGGER.error(f"Error setting AC temperature for {self.entity_id}: {e}")
            return False
    
    async def _send_fan_mode_command(self, fan_mode: str) -> bool:
        """Send AC fan mode command."""
        try:
            # Map fan mode to TIS value
            fan_mapping = {
                "auto": 0,
                "low": 1,
                "medium": 2,
                "high": 3
            }
            
            tis_fan_speed = fan_mapping.get(fan_mode, 0)
            
            op_code = TIS_OPCODES["AC_SET_FAN_SPEED"]
            additional_data = [tis_fan_speed]
            
            success = await self.async_send_command(op_code, additional_data)
            
            if success:
                _LOGGER.debug(f"AC {self.entity_id} fan mode set to {fan_mode}")
            
            return success
            
        except Exception as e:
            _LOGGER.error(f"Error setting AC fan mode for {self.entity_id}: {e}")
            return False
    
    async def _send_preset_mode_command(self, preset_mode: str) -> bool:
        """Send AC preset mode command."""
        try:
            # Use general device control for preset modes
            op_code = TIS_OPCODES["DEVICE_ON"]
            
            # Map preset modes to additional data
            preset_mapping = {
                "none": [0],
                "eco": [1],
                "turbo": [2],
                "sleep": [3]
            }
            
            additional_data = preset_mapping.get(preset_mode, [0])
            
            success = await self.async_send_command(op_code, additional_data)
            
            if success:
                _LOGGER.debug(f"AC {self.entity_id} preset mode set to {preset_mode}")
            
            return success
            
        except Exception as e:
            _LOGGER.error(f"Error setting AC preset mode for {self.entity_id}: {e}")
            return False
    
    def _update_climate_state_from_data(self, device_state: Dict[str, Any]) -> None:
        """Update AC state from device state data."""
        # Look for AC data in device state
        if "ac" in device_state:
            ac_data = device_state["ac"]
            if isinstance(ac_data, dict):
                # Update power/HVAC mode
                power = ac_data.get("power")
                if power == "on":
                    mode = ac_data.get("mode", "auto")
                    mode_mapping = {
                        "cool": HVACMode.COOL,
                        "heat": HVACMode.HEAT,
                        "fan": HVACMode.FAN_ONLY,
                        "auto": HVACMode.AUTO
                    }
                    self._hvac_mode = mode_mapping.get(mode, HVACMode.AUTO)
                    
                    # Determine current action
                    if mode == "cool":
                        self._hvac_action = HVACAction.COOLING
                    elif mode == "heat":
                        self._hvac_action = HVACAction.HEATING
                    elif mode == "fan":
                        self._hvac_action = HVACAction.FAN
                    else:
                        self._hvac_action = HVACAction.IDLE
                
                elif power == "off":
                    self._hvac_mode = HVACMode.OFF
                    self._hvac_action = HVACAction.OFF
                
                # Update target temperature
                temperature = ac_data.get("temperature")
                if temperature is not None:
                    self._target_temperature = float(temperature)
                
                # Update fan mode
                fan_speed = ac_data.get("fan_speed")
                if fan_speed is not None:
                    fan_mapping = {0: "auto", 1: "low", 2: "medium", 3: "high"}
                    self._fan_mode = fan_mapping.get(fan_speed, "auto")
        
        # Update current temperature from general device state
        current_temp = device_state.get("current_temperature")
        if current_temp is not None:
            self._current_temperature = float(current_temp)
        
        # Update current humidity if available
        current_humidity = device_state.get("current_humidity")
        if current_humidity is not None:
            self._current_humidity = int(current_humidity)
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional AC controller attributes."""
        attrs = super().extra_state_attributes
        
        device_state = self.coordinator.get_device_state(self.device_key)
        if device_state and "ac" in device_state:
            ac_data = device_state["ac"]
            if isinstance(ac_data, dict):
                # Add AC-specific attributes
                attrs.update({
                    "ac_power": ac_data.get("power", "unknown"),
                    "ac_mode": ac_data.get("mode", "unknown"),
                    "ac_temperature": ac_data.get("temperature"),
                    "ac_fan_speed": ac_data.get("fan_speed"),
                })
        
        return attrs

class TISThermostatEntity(TISClimateEntity):
    """Thermostat entity for TIS thermostat devices."""
    
    def __init__(
        self,
        coordinator: TISDataUpdateCoordinator,
        device_key: str,
        device_name: str,
    ) -> None:
        """Initialize thermostat entity."""
        
        super().__init__(
            coordinator=coordinator,
            device_key=device_key,
            entity_key="thermostat",
            entity_name=f"{device_name} Thermostat",
            hvac_modes=[HVACMode.OFF, HVACMode.HEAT, HVACMode.AUTO],
            supported_features=(
                ClimateEntityFeature.TARGET_TEMPERATURE |
                ClimateEntityFeature.PRESET_MODE |
                ClimateEntityFeature.TURN_ON |
                ClimateEntityFeature.TURN_OFF
            )
        )
        
        # Thermostat-specific settings
        self._attr_preset_modes = ["none", "away", "comfort", "eco"]
        self._attr_min_temp = 10
        self._attr_max_temp = 35
    
    async def _send_hvac_mode_command(self, hvac_mode: HVACMode) -> bool:
        """Send thermostat HVAC mode command."""
        try:
            if hvac_mode == HVACMode.OFF:
                op_code = TIS_OPCODES["DEVICE_OFF"]
                additional_data = []
            else:
                op_code = TIS_OPCODES["DEVICE_ON"]
                
                # Map HVAC mode to thermostat mode
                if hvac_mode == HVACMode.HEAT:
                    thermostat_mode = 1  # Heat mode
                elif hvac_mode == HVACMode.AUTO:
                    thermostat_mode = 2  # Auto mode
                else:
                    thermostat_mode = 2  # Default to auto
                
                additional_data = [thermostat_mode]
            
            success = await self.async_send_command(op_code, additional_data)
            
            if success:
                _LOGGER.debug(f"Thermostat {self.entity_id} HVAC mode set to {hvac_mode}")
            
            return success
            
        except Exception as e:
            _LOGGER.error(f"Error setting thermostat HVAC mode for {self.entity_id}: {e}")
            return False
    
    async def _send_temperature_command(self, temperature: float) -> bool:
        """Send thermostat temperature command."""
        try:
            # Use lighting dimmer command for temperature adjustment (common in TIS thermostats)
            op_code = TIS_OPCODES["LIGHT_DIMMER"]
            temp_value = int(temperature)
            additional_data = [temp_value]
            
            success = await self.async_send_command(op_code, additional_data)
            
            if success:
                _LOGGER.debug(f"Thermostat {self.entity_id} temperature set to {temperature}°C")
            
            return success
            
        except Exception as e:
            _LOGGER.error(f"Error setting thermostat temperature for {self.entity_id}: {e}")
            return False
    
    async def _send_fan_mode_command(self, fan_mode: str) -> bool:
        """Thermostats typically don't have fan mode control."""
        return True  # No-op for thermostats
    
    async def _send_preset_mode_command(self, preset_mode: str) -> bool:
        """Send thermostat preset mode command."""
        try:
            op_code = TIS_OPCODES["DEVICE_ON"]
            
            # Map preset modes
            preset_mapping = {
                "none": [0],
                "away": [1],
                "comfort": [2],
                "eco": [3]
            }
            
            additional_data = preset_mapping.get(preset_mode, [0])
            
            success = await self.async_send_command(op_code, additional_data)
            
            if success:
                _LOGGER.debug(f"Thermostat {self.entity_id} preset mode set to {preset_mode}")
            
            return success
            
        except Exception as e:
            _LOGGER.error(f"Error setting thermostat preset mode for {self.entity_id}: {e}")
            return False
    
    def _update_climate_state_from_data(self, device_state: Dict[str, Any]) -> None:
        """Update thermostat state from device state data."""
        # Look for thermostat data
        if "thermostat" in device_state:
            thermostat_data = device_state["thermostat"]
            if isinstance(thermostat_data, dict):
                # Update power/mode
                power = thermostat_data.get("power")
                if power == "on":
                    mode = thermostat_data.get("mode", "heat")
                    if mode == "heat":
                        self._hvac_mode = HVACMode.HEAT
                        self._hvac_action = HVACAction.HEATING
                    elif mode == "auto":
                        self._hvac_mode = HVACMode.AUTO
                        self._hvac_action = HVACAction.IDLE
                elif power == "off":
                    self._hvac_mode = HVACMode.OFF
                    self._hvac_action = HVACAction.OFF
                
                # Update target temperature
                target_temp = thermostat_data.get("target_temperature")
                if target_temp is not None:
                    self._target_temperature = float(target_temp)
        
        # Update current temperature
        current_temp = device_state.get("current_temperature")
        if current_temp is not None:
            self._current_temperature = float(current_temp)

class TISFloorHeatingEntity(TISClimateEntity):
    """Floor heating controller entity for TIS floor heating devices."""
    
    def __init__(
        self,
        coordinator: TISDataUpdateCoordinator,
        device_key: str,
        device_name: str,
    ) -> None:
        """Initialize floor heating entity."""
        
        super().__init__(
            coordinator=coordinator,
            device_key=device_key,
            entity_key="floor_heating",
            entity_name=f"{device_name} Floor Heating",
            hvac_modes=[HVACMode.OFF, HVACMode.HEAT],
            supported_features=(
                ClimateEntityFeature.TARGET_TEMPERATURE |
                ClimateEntityFeature.TURN_ON |
                ClimateEntityFeature.TURN_OFF
            )
        )
        
        # Floor heating specific settings
        self._attr_min_temp = 15
        self._attr_max_temp = 40
    
    async def _send_hvac_mode_command(self, hvac_mode: HVACMode) -> bool:
        """Send floor heating mode command."""
        try:
            if hvac_mode == HVACMode.OFF:
                op_code = TIS_OPCODES["DEVICE_OFF"]
            else:  # HVACMode.HEAT
                op_code = TIS_OPCODES["DEVICE_ON"]
            
            success = await self.async_send_command(op_code)
            
            if success:
                _LOGGER.debug(f"Floor heating {self.entity_id} turned {'on' if hvac_mode != HVACMode.OFF else 'off'}")
            
            return success
            
        except Exception as e:
            _LOGGER.error(f"Error controlling floor heating {self.entity_id}: {e}")
            return False
    
    async def _send_temperature_command(self, temperature: float) -> bool:
        """Send floor heating temperature command."""
        try:
            # Use dimmer command for temperature control
            op_code = TIS_OPCODES["LIGHT_DIMMER"]
            temp_value = int(temperature)
            additional_data = [temp_value]
            
            success = await self.async_send_command(op_code, additional_data)
            
            if success:
                _LOGGER.debug(f"Floor heating {self.entity_id} temperature set to {temperature}°C")
            
            return success
            
        except Exception as e:
            _LOGGER.error(f"Error setting floor heating temperature for {self.entity_id}: {e}")
            return False
    
    async def _send_fan_mode_command(self, fan_mode: str) -> bool:
        """Floor heating doesn't have fan mode."""
        return True  # No-op
    
    async def _send_preset_mode_command(self, preset_mode: str) -> bool:
        """Floor heating doesn't have preset modes."""
        return True  # No-op
    
    def _update_climate_state_from_data(self, device_state: Dict[str, Any]) -> None:
        """Update floor heating state from device state data."""
        # Look for floor heating data
        if "floor_heating" in device_state:
            heating_data = device_state["floor_heating"]
            if isinstance(heating_data, dict):
                power = heating_data.get("power")
                if power == "on":
                    self._hvac_mode = HVACMode.HEAT
                    self._hvac_action = HVACAction.HEATING
                elif power == "off":
                    self._hvac_mode = HVACMode.OFF
                    self._hvac_action = HVACAction.OFF
                
                target_temp = heating_data.get("target_temperature")
                if target_temp is not None:
                    self._target_temperature = float(target_temp)
        
        # Check generic state
        elif "state" in device_state:
            state = device_state["state"]
            if state == "on":
                self._hvac_mode = HVACMode.HEAT
                self._hvac_action = HVACAction.HEATING
            elif state == "off":
                self._hvac_mode = HVACMode.OFF
                self._hvac_action = HVACAction.OFF
        
        # Update current temperature
        current_temp = device_state.get("current_temperature")
        if current_temp is not None:
            self._current_temperature = float(current_temp)

class TISGenericClimateEntity(TISClimateEntity):
    """Generic climate entity for unknown TIS climate devices."""
    
    def __init__(
        self,
        coordinator: TISDataUpdateCoordinator,
        device_key: str,
        device_name: str,
        climate_index: int = 0,
    ) -> None:
        """Initialize generic climate entity."""
        
        entity_key = f"climate_{climate_index}"
        entity_name = f"{device_name} Climate"
        if climate_index > 0:
            entity_name += f" {climate_index + 1}"
        
        super().__init__(
            coordinator=coordinator,
            device_key=device_key,
            entity_key=entity_key,
            entity_name=entity_name,
            hvac_modes=[HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL, HVACMode.AUTO],
            supported_features=(
                ClimateEntityFeature.TARGET_TEMPERATURE |
                ClimateEntityFeature.TURN_ON |
                ClimateEntityFeature.TURN_OFF
            )
        )
        
        self.climate_index = climate_index
    
    async def _send_hvac_mode_command(self, hvac_mode: HVACMode) -> bool:
        """Send generic climate mode command."""
        try:
            if hvac_mode == HVACMode.OFF:
                op_code = TIS_OPCODES["DEVICE_OFF"]
                additional_data = []
            else:
                op_code = TIS_OPCODES["DEVICE_ON"]
                
                # Map HVAC modes to generic values
                mode_mapping = {
                    HVACMode.HEAT: 1,
                    HVACMode.COOL: 2,
                    HVACMode.AUTO: 3
                }
                
                mode_value = mode_mapping.get(hvac_mode, 3)
                additional_data = [self.climate_index, mode_value]
            
            success = await self.async_send_command(op_code, additional_data)
            return success
            
        except Exception as e:
            _LOGGER.error(f"Error setting generic climate mode for {self.entity_id}: {e}")
            return False
    
    async def _send_temperature_command(self, temperature: float) -> bool:
        """Send generic temperature command."""
        try:
            op_code = TIS_OPCODES["LIGHT_DIMMER"]  # Use dimmer for temperature
            temp_value = int(temperature)
            additional_data = [self.climate_index, temp_value]
            
            success = await self.async_send_command(op_code, additional_data)
            return success
            
        except Exception as e:
            _LOGGER.error(f"Error setting generic climate temperature for {self.entity_id}: {e}")
            return False
    
    async def _send_fan_mode_command(self, fan_mode: str) -> bool:
        """Send generic fan mode command."""
        return True  # No-op for generic climate
    
    async def _send_preset_mode_command(self, preset_mode: str) -> bool:
        """Send generic preset mode command."""
        return True  # No-op for generic climate
    
    def _update_climate_state_from_data(self, device_state: Dict[str, Any]) -> None:
        """Update generic climate state from device state data."""
        # Try to find climate data for this index
        climate_data = device_state.get(f"climate_{self.climate_index}")
        if climate_data is not None and isinstance(climate_data, dict):
            power = climate_data.get("power")
            if power == "on":
                self._hvac_mode = HVACMode.AUTO  # Default to auto
                self._hvac_action = HVACAction.IDLE
            elif power == "off":
                self._hvac_mode = HVACMode.OFF
                self._hvac_action = HVACAction.OFF
            
            target_temp = climate_data.get("target_temperature")
            if target_temp is not None:
                self._target_temperature = float(target_temp)
        
        # Check for generic state (only for first climate device)
        elif self.climate_index == 0:
            state = device_state.get("state")
            if state == "on":
                self._hvac_mode = HVACMode.AUTO
                self._hvac_action = HVACAction.IDLE
            elif state == "off":
                self._hvac_mode = HVACMode.OFF
                self._hvac_action = HVACAction.OFF
        
        # Update current temperature
        current_temp = device_state.get("current_temperature")
        if current_temp is not None:
            self._current_temperature = float(current_temp)
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional generic climate attributes."""
        attrs = super().extra_state_attributes
        attrs["climate_index"] = self.climate_index
        
        # Add raw device state for debugging
        device_state = self.coordinator.get_device_state(self.device_key)
        if device_state:
            attrs["raw_data"] = str(device_state)
        
        return attrs
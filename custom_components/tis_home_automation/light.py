"""
Light platform for TIS Home Automation integration.
Supports TIS dimmer devices including multi-gang dimmers.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.color import (
    color_temperature_kelvin_to_mired,
    color_temperature_mired_to_kelvin,
)

from .const import (
    DOMAIN,
    TIS_DEVICE_TYPES,
    TIS_OPCODES,
    DEVICE_CAPABILITIES,
    ENTITY_DEFINITIONS,
)
from .coordinator import TISDataUpdateCoordinator
from .entity import TISBaseEntity, TISMultiChannelEntity, TISDeviceWrapper

_LOGGER = logging.getLogger(__name__)

# TIS dimmer constants
MIN_BRIGHTNESS = 1
MAX_BRIGHTNESS = 255
MIN_COLOR_TEMP_KELVIN = 2700  # Warm white
MAX_COLOR_TEMP_KELVIN = 6500  # Cool white

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up TIS light entities from config entry."""
    
    # Get coordinator and devices from hass data
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    coordinator: TISDataUpdateCoordinator = entry_data["coordinator"]
    discovered_devices = entry_data["discovered_devices"]
    
    entities = []
    
    # Create light entities for each discovered device
    for device_key, tis_device in discovered_devices.items():
        device_wrapper = TISDeviceWrapper(tis_device, coordinator)
        device_type_name = device_wrapper.device_type_name
        
        # Check if device has light capabilities
        capabilities = DEVICE_CAPABILITIES.get(device_type_name, [])
        
        light_indices = [i for i, cap in enumerate(capabilities) if cap == "light"]
        
        for light_index in light_indices:
            # Determine if this is a multi-gang dimmer
            light_count = len([cap for cap in capabilities if cap == "light"])
            
            if light_count > 1:
                # Multi-gang dimmer
                gang_number = light_indices.index(light_index)
                entity = TISMultiGangLightEntity(
                    coordinator=coordinator,
                    device_key=device_key,
                    gang_index=gang_number,
                    device_name=tis_device.name
                )
            else:
                # Single dimmer/light
                entity_class = _get_light_entity_class(device_type_name)
                entity = entity_class(
                    coordinator=coordinator,
                    device_key=device_key,
                    device_name=tis_device.name
                )
            
            entities.append(entity)
            _LOGGER.debug(f"Added TIS light entity: {entity.name}")
    
    if entities:
        async_add_entities(entities, True)
        _LOGGER.info(f"Added {len(entities)} TIS light entities")

def _get_light_entity_class(device_type_name: str):
    """Get appropriate light entity class based on device type."""
    if "rgb" in device_type_name.lower():
        return TISRGBLightEntity
    elif "color_temp" in device_type_name.lower() or "tunable" in device_type_name.lower():
        return TISColorTempLightEntity
    else:
        return TISDimmableLightEntity

class TISLightEntity(TISBaseEntity, LightEntity):
    """Base class for TIS light entities."""
    
    def __init__(
        self,
        coordinator: TISDataUpdateCoordinator,
        device_key: str,
        entity_key: str,
        entity_name: str,
        color_modes: set[ColorMode] = None,
        supported_features: LightEntityFeature = LightEntityFeature(0),
    ) -> None:
        """Initialize TIS light entity."""
        
        # Get light icon from entity definitions
        light_def = ENTITY_DEFINITIONS.get("light", {})
        
        super().__init__(
            coordinator=coordinator,
            device_key=device_key,
            entity_key=entity_key,
            entity_name=entity_name,
            entity_type="light",
            icon=light_def.get("icon"),
            device_class=light_def.get("device_class")
        )
        
        # Light state
        self._is_on = False
        self._brightness = 255  # 0-255 range
        self._rgb_color: Optional[tuple[int, int, int]] = None
        self._color_temp_kelvin: Optional[int] = None
        
        # Set supported color modes and features
        self._attr_color_mode = ColorMode.BRIGHTNESS
        self._attr_supported_color_modes = color_modes or {ColorMode.BRIGHTNESS}
        self._attr_supported_features = supported_features
        
        # Set brightness range
        if ColorMode.BRIGHTNESS in self._attr_supported_color_modes:
            self._attr_min_mireds = color_temperature_kelvin_to_mired(MAX_COLOR_TEMP_KELVIN)
            self._attr_max_mireds = color_temperature_kelvin_to_mired(MIN_COLOR_TEMP_KELVIN)
    
    @property
    def is_on(self) -> bool:
        """Return True if light is on."""
        return self._is_on
    
    @property
    def brightness(self) -> Optional[int]:
        """Return brightness of light (0-255)."""
        return self._brightness if self._is_on else None
    
    @property
    def rgb_color(self) -> Optional[tuple[int, int, int]]:
        """Return RGB color of light."""
        return self._rgb_color if self._is_on and ColorMode.RGB in self.supported_color_modes else None
    
    @property
    def color_temp_kelvin(self) -> Optional[int]:
        """Return color temperature in Kelvin."""
        return self._color_temp_kelvin if self._is_on and ColorMode.COLOR_TEMP in self.supported_color_modes else None
    
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on with specified parameters."""
        brightness = kwargs.get(ATTR_BRIGHTNESS, self._brightness)
        rgb_color = kwargs.get(ATTR_RGB_COLOR)
        color_temp = kwargs.get(ATTR_COLOR_TEMP)
        
        # Convert mired to Kelvin if needed
        color_temp_kelvin = None
        if color_temp is not None:
            color_temp_kelvin = color_temperature_mired_to_kelvin(color_temp)
        
        success = await self._send_light_command(
            turn_on=True,
            brightness=brightness,
            rgb_color=rgb_color,
            color_temp_kelvin=color_temp_kelvin
        )
        
        if success:
            self._is_on = True
            self._brightness = brightness
            if rgb_color is not None:
                self._rgb_color = rgb_color
            if color_temp_kelvin is not None:
                self._color_temp_kelvin = color_temp_kelvin
            self.async_write_ha_state()
    
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        success = await self._send_light_command(turn_on=False)
        if success:
            self._is_on = False
            self.async_write_ha_state()
    
    async def _send_light_command(
        self,
        turn_on: bool,
        brightness: Optional[int] = None,
        rgb_color: Optional[tuple[int, int, int]] = None,
        color_temp_kelvin: Optional[int] = None
    ) -> bool:
        """Send light command to device."""
        # This method should be implemented by subclasses
        raise NotImplementedError()
    
    def _update_from_coordinator_data(self) -> None:
        """Update light state from coordinator data."""
        device_state = self.coordinator.get_device_state(self.device_key)
        if not device_state:
            return
        
        # Update light state - implementation depends on subclass
        self._update_light_state_from_data(device_state)
    
    def _update_light_state_from_data(self, device_state: Dict[str, Any]) -> None:
        """Update light state from device state data."""
        # This method should be implemented by subclasses
        pass

class TISDimmableLightEntity(TISLightEntity):
    """Single dimmable light entity for TIS dimmer devices."""
    
    def __init__(
        self,
        coordinator: TISDataUpdateCoordinator,
        device_key: str,
        device_name: str,
    ) -> None:
        """Initialize dimmable light entity."""
        
        super().__init__(
            coordinator=coordinator,
            device_key=device_key,
            entity_key="light",
            entity_name=device_name,
            color_modes={ColorMode.BRIGHTNESS}
        )
    
    async def _send_light_command(
        self,
        turn_on: bool,
        brightness: Optional[int] = None,
        rgb_color: Optional[tuple[int, int, int]] = None,
        color_temp_kelvin: Optional[int] = None
    ) -> bool:
        """Send dimmer command to single dimmer device."""
        try:
            if turn_on:
                if brightness is not None and brightness != 255:
                    # Send dimmer command with brightness level
                    op_code = TIS_OPCODES["LIGHT_DIMMER"]
                    # Convert HA brightness (0-255) to TIS brightness (0-100)
                    tis_brightness = int((brightness / 255.0) * 100)
                    additional_data = [tis_brightness]
                else:
                    # Turn on at full brightness
                    op_code = TIS_OPCODES["LIGHT_ON"]
                    additional_data = []
            else:
                # Turn off
                op_code = TIS_OPCODES["LIGHT_OFF"]
                additional_data = []
            
            success = await self.async_send_command(op_code, additional_data)
            
            if success:
                action = "dimmed" if turn_on and brightness != 255 else ("on" if turn_on else "off")
                _LOGGER.debug(f"Dimmer {self.entity_id} turned {action}")
            else:
                _LOGGER.warning(f"Failed to control dimmer {self.entity_id}")
            
            return success
            
        except Exception as e:
            _LOGGER.error(f"Error sending dimmer command to {self.entity_id}: {e}")
            return False
    
    def _update_light_state_from_data(self, device_state: Dict[str, Any]) -> None:
        """Update single dimmer state from device state data."""
        # Look for dimmer data in device state
        if "dimmers" in device_state:
            dimmers_data = device_state["dimmers"]
            if isinstance(dimmers_data, list) and dimmers_data:
                dimmer_data = dimmers_data[0]  # First (and only) dimmer
                if isinstance(dimmer_data, dict):
                    state = dimmer_data.get("state")
                    if state == "on":
                        self._is_on = True
                    elif state == "off":
                        self._is_on = False
                    
                    brightness = dimmer_data.get("brightness")
                    if brightness is not None:
                        # Convert TIS brightness (0-100) to HA brightness (0-255)
                        self._brightness = int((brightness / 100.0) * 255)
        
        # Fallback: check for generic light data
        elif "light" in device_state:
            light_data = device_state["light"]
            if isinstance(light_data, dict):
                if light_data.get("state") == "on":
                    self._is_on = True
                elif light_data.get("state") == "off":
                    self._is_on = False
                
                brightness = light_data.get("brightness")
                if brightness is not None:
                    self._brightness = int((brightness / 100.0) * 255)

class TISMultiGangLightEntity(TISMultiChannelEntity, LightEntity):
    """Multi-gang dimmer entity for TIS devices."""
    
    def __init__(
        self,
        coordinator: TISDataUpdateCoordinator,
        device_key: str,
        gang_index: int,
        device_name: str,
    ) -> None:
        """Initialize multi-gang light entity."""
        
        # Get light icon from entity definitions
        light_def = ENTITY_DEFINITIONS.get("light", {})
        
        super().__init__(
            coordinator=coordinator,
            device_key=device_key,
            channel_index=gang_index,
            entity_name=f"{device_name} Dimmer",  # Will become "Device Dimmer 1", "Device Dimmer 2", etc.
            entity_type="light",
            icon=light_def.get("icon"),
            device_class=light_def.get("device_class")
        )
        
        # Light state
        self._is_on = False
        self._brightness = 255
        
        # Set supported features
        self._attr_color_mode = ColorMode.BRIGHTNESS
        self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}
    
    @property
    def is_on(self) -> bool:
        """Return True if this gang is on."""
        return self._is_on
    
    @property
    def brightness(self) -> Optional[int]:
        """Return brightness of this gang (0-255)."""
        return self._brightness if self._is_on else None
    
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn this gang on."""
        brightness = kwargs.get(ATTR_BRIGHTNESS, self._brightness)
        success = await self._send_gang_light_command(True, brightness)
        if success:
            self._is_on = True
            self._brightness = brightness
            self.async_write_ha_state()
    
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn this gang off."""
        success = await self._send_gang_light_command(False)
        if success:
            self._is_on = False
            self.async_write_ha_state()
    
    async def _send_gang_light_command(self, turn_on: bool, brightness: Optional[int] = None) -> bool:
        """Send command to specific gang of multi-gang dimmer."""
        try:
            # Build gang-specific command
            if turn_on:
                if brightness is not None and brightness != 255:
                    # Send dimmer command with brightness level
                    op_code = TIS_OPCODES["LIGHT_DIMMER"]
                    # Convert HA brightness (0-255) to TIS brightness (0-100)
                    tis_brightness = int((brightness / 255.0) * 100)
                    additional_data = [self.channel_index, tis_brightness]
                else:
                    # Turn on at full brightness
                    op_code = TIS_OPCODES["LIGHT_ON"]
                    additional_data = [self.channel_index]
            else:
                # Turn off
                op_code = TIS_OPCODES["LIGHT_OFF"]
                additional_data = [self.channel_index]
            
            success = await self.async_send_command(op_code, additional_data)
            
            if success:
                action = "dimmed" if turn_on and brightness != 255 else ("on" if turn_on else "off")
                _LOGGER.debug(
                    f"Multi-gang dimmer {self.entity_id} gang {self.channel_index + 1} {action}"
                )
            else:
                _LOGGER.warning(
                    f"Failed to control multi-gang dimmer {self.entity_id} gang {self.channel_index + 1}"
                )
            
            return success
            
        except Exception as e:
            _LOGGER.error(f"Error sending gang light command to {self.entity_id}: {e}")
            return False
    
    def _update_from_coordinator_data(self) -> None:
        """Update gang light state from coordinator data."""
        device_state = self.coordinator.get_device_state(self.device_key)
        if not device_state:
            return
        
        # Get data for this specific gang
        gang_data = self.get_channel_data("dimmers")
        if isinstance(gang_data, dict):
            state = gang_data.get("state")
            if state == "on":
                self._is_on = True
            elif state == "off":
                self._is_on = False
            
            brightness = gang_data.get("brightness")
            if brightness is not None:
                # Convert TIS brightness (0-100) to HA brightness (0-255)
                self._brightness = int((brightness / 100.0) * 255)

class TISColorTempLightEntity(TISLightEntity):
    """Color temperature adjustable light entity for TIS devices."""
    
    def __init__(
        self,
        coordinator: TISDataUpdateCoordinator,
        device_key: str,
        device_name: str,
    ) -> None:
        """Initialize color temperature light entity."""
        
        super().__init__(
            coordinator=coordinator,
            device_key=device_key,
            entity_key="light",
            entity_name=device_name,
            color_modes={ColorMode.COLOR_TEMP, ColorMode.BRIGHTNESS},
            supported_features=LightEntityFeature.TRANSITION
        )
        
        # Set initial color mode
        self._attr_color_mode = ColorMode.COLOR_TEMP
        self._color_temp_kelvin = 4000  # Default warm white
    
    async def _send_light_command(
        self,
        turn_on: bool,
        brightness: Optional[int] = None,
        rgb_color: Optional[tuple[int, int, int]] = None,
        color_temp_kelvin: Optional[int] = None
    ) -> bool:
        """Send color temperature light command."""
        try:
            if turn_on:
                op_code = TIS_OPCODES["LIGHT_ON"]
                additional_data = []
                
                # Add brightness if specified
                if brightness is not None:
                    tis_brightness = int((brightness / 255.0) * 100)
                    additional_data.append(tis_brightness)
                
                # Add color temperature if specified
                if color_temp_kelvin is not None:
                    # Convert Kelvin to TIS color temp format (assume 0-100 range)
                    # Map 2700K-6500K to 0-100
                    temp_range = MAX_COLOR_TEMP_KELVIN - MIN_COLOR_TEMP_KELVIN
                    normalized_temp = (color_temp_kelvin - MIN_COLOR_TEMP_KELVIN) / temp_range
                    tis_color_temp = int(normalized_temp * 100)
                    additional_data.append(tis_color_temp)
            else:
                op_code = TIS_OPCODES["LIGHT_OFF"]
                additional_data = []
            
            success = await self.async_send_command(op_code, additional_data)
            
            if success:
                _LOGGER.debug(f"Color temp light {self.entity_id} controlled successfully")
            
            return success
            
        except Exception as e:
            _LOGGER.error(f"Error controlling color temp light {self.entity_id}: {e}")
            return False
    
    def _update_light_state_from_data(self, device_state: Dict[str, Any]) -> None:
        """Update color temp light state from device state data."""
        if "light" in device_state:
            light_data = device_state["light"]
            if isinstance(light_data, dict):
                if light_data.get("state") == "on":
                    self._is_on = True
                elif light_data.get("state") == "off":
                    self._is_on = False
                
                brightness = light_data.get("brightness")
                if brightness is not None:
                    self._brightness = int((brightness / 100.0) * 255)
                
                color_temp = light_data.get("color_temp")
                if color_temp is not None:
                    # Convert TIS color temp (0-100) to Kelvin
                    normalized_temp = color_temp / 100.0
                    temp_range = MAX_COLOR_TEMP_KELVIN - MIN_COLOR_TEMP_KELVIN
                    self._color_temp_kelvin = int(MIN_COLOR_TEMP_KELVIN + (normalized_temp * temp_range))

class TISRGBLightEntity(TISLightEntity):
    """RGB light entity for TIS RGB devices."""
    
    def __init__(
        self,
        coordinator: TISDataUpdateCoordinator,
        device_key: str,
        device_name: str,
    ) -> None:
        """Initialize RGB light entity."""
        
        super().__init__(
            coordinator=coordinator,
            device_key=device_key,
            entity_key="light",
            entity_name=device_name,
            color_modes={ColorMode.RGB, ColorMode.BRIGHTNESS},
            supported_features=LightEntityFeature.TRANSITION | LightEntityFeature.EFFECT
        )
        
        # Set initial color mode
        self._attr_color_mode = ColorMode.RGB
        self._rgb_color = (255, 255, 255)  # Default white
    
    async def _send_light_command(
        self,
        turn_on: bool,
        brightness: Optional[int] = None,
        rgb_color: Optional[tuple[int, int, int]] = None,
        color_temp_kelvin: Optional[int] = None
    ) -> bool:
        """Send RGB light command."""
        try:
            if turn_on:
                op_code = TIS_OPCODES["LIGHT_ON"]
                additional_data = []
                
                # Add brightness if specified
                if brightness is not None:
                    tis_brightness = int((brightness / 255.0) * 100)
                    additional_data.append(tis_brightness)
                
                # Add RGB color if specified
                if rgb_color is not None:
                    r, g, b = rgb_color
                    additional_data.extend([r, g, b])
            else:
                op_code = TIS_OPCODES["LIGHT_OFF"]
                additional_data = []
            
            success = await self.async_send_command(op_code, additional_data)
            
            if success:
                _LOGGER.debug(f"RGB light {self.entity_id} controlled successfully")
            
            return success
            
        except Exception as e:
            _LOGGER.error(f"Error controlling RGB light {self.entity_id}: {e}")
            return False
    
    def _update_light_state_from_data(self, device_state: Dict[str, Any]) -> None:
        """Update RGB light state from device state data."""
        if "light" in device_state:
            light_data = device_state["light"]
            if isinstance(light_data, dict):
                if light_data.get("state") == "on":
                    self._is_on = True
                elif light_data.get("state") == "off":
                    self._is_on = False
                
                brightness = light_data.get("brightness")
                if brightness is not None:
                    self._brightness = int((brightness / 100.0) * 255)
                
                rgb = light_data.get("rgb")
                if rgb is not None and len(rgb) >= 3:
                    self._rgb_color = (rgb[0], rgb[1], rgb[2])

# Factory function for creating appropriate light entities
def create_light_entity(
    coordinator: TISDataUpdateCoordinator,
    device_wrapper: TISDeviceWrapper,
    light_index: int = 0
) -> TISLightEntity:
    """Create appropriate light entity based on device type."""
    
    device_type_name = device_wrapper.device_type_name
    device_key = device_wrapper.device_key
    device_name = device_wrapper.tis_device.name
    
    # Get device capabilities to determine light count
    capabilities = DEVICE_CAPABILITIES.get(device_type_name, [])
    light_count = len([cap for cap in capabilities if cap == "light"])
    
    # Determine entity class based on device type
    if "rgb" in device_type_name.lower():
        entity_class = TISRGBLightEntity
    elif "color_temp" in device_type_name.lower() or "tunable" in device_type_name.lower():
        entity_class = TISColorTempLightEntity
    else:
        entity_class = TISDimmableLightEntity
    
    # Create multi-gang or single entity
    if light_count > 1:
        return TISMultiGangLightEntity(
            coordinator=coordinator,
            device_key=device_key,
            gang_index=light_index,
            device_name=device_name
        )
    else:
        return entity_class(
            coordinator=coordinator,
            device_key=device_key,
            device_name=device_name
        )
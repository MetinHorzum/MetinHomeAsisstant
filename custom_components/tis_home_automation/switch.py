"""
Switch platform for TIS Home Automation integration.
Supports TIS switch devices including multi-gang switches.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from homeassistant.components.switch import SwitchEntity
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
from .entity import TISBaseEntity, TISMultiChannelEntity, TISDeviceWrapper

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up TIS switch entities from config entry."""
    
    # Get coordinator and devices from hass data
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    coordinator: TISDataUpdateCoordinator = entry_data["coordinator"]
    discovered_devices = entry_data["discovered_devices"]
    
    entities = []
    
    # Create switch entities for each discovered device
    for device_key, tis_device in discovered_devices.items():
        device_wrapper = TISDeviceWrapper(tis_device, coordinator)
        device_type_name = device_wrapper.device_type_name
        
        # Check if device has switch capabilities
        capabilities = DEVICE_CAPABILITIES.get(device_type_name, [])
        
        switch_indices = [i for i, cap in enumerate(capabilities) if cap == "switch"]
        
        for switch_index in switch_indices:
            # Determine if this is a multi-gang switch
            gang_count = len([cap for cap in capabilities if cap == "switch"])
            
            if gang_count > 1:
                # Multi-gang switch
                gang_number = switch_indices.index(switch_index)
                entity = TISMultiGangSwitchEntity(
                    coordinator=coordinator,
                    device_key=device_key,
                    gang_index=gang_number,
                    device_name=tis_device.name
                )
            else:
                # Single switch
                entity = TISSingleSwitchEntity(
                    coordinator=coordinator,
                    device_key=device_key,
                    device_name=tis_device.name
                )
            
            entities.append(entity)
            _LOGGER.debug(f"Added TIS switch entity: {entity.name}")
    
    if entities:
        async_add_entities(entities, True)
        _LOGGER.info(f"Added {len(entities)} TIS switch entities")

class TISSwitchEntity(TISBaseEntity, SwitchEntity):
    """Base class for TIS switch entities."""
    
    def __init__(
        self,
        coordinator: TISDataUpdateCoordinator,
        device_key: str,
        entity_key: str,
        entity_name: str,
    ) -> None:
        """Initialize TIS switch entity."""
        
        # Get switch icon from entity definitions
        switch_def = ENTITY_DEFINITIONS.get("switch", {})
        
        super().__init__(
            coordinator=coordinator,
            device_key=device_key,
            entity_key=entity_key,
            entity_name=entity_name,
            entity_type="switch",
            icon=switch_def.get("icon"),
            device_class=switch_def.get("device_class")
        )
        
        # Switch state
        self._is_on = False
        self._available = True
    
    @property
    def is_on(self) -> bool:
        """Return True if switch is on."""
        return self._is_on
    
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        success = await self._send_switch_command(True)
        if success:
            self._is_on = True
            self.async_write_ha_state()
    
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        success = await self._send_switch_command(False)
        if success:
            self._is_on = False
            self.async_write_ha_state()
    
    async def _send_switch_command(self, turn_on: bool) -> bool:
        """Send switch command to device."""
        # This method should be implemented by subclasses
        # to handle specific switch command formats
        raise NotImplementedError()
    
    def _update_from_coordinator_data(self) -> None:
        """Update switch state from coordinator data."""
        device_state = self.coordinator.get_device_state(self.device_key)
        if not device_state:
            return
        
        # Update switch state - implementation depends on subclass
        self._update_switch_state_from_data(device_state)
    
    def _update_switch_state_from_data(self, device_state: Dict[str, Any]) -> None:
        """Update switch state from device state data."""
        # This method should be implemented by subclasses
        pass

class TISSingleSwitchEntity(TISSwitchEntity):
    """Single switch entity for TIS devices."""
    
    def __init__(
        self,
        coordinator: TISDataUpdateCoordinator,
        device_key: str,
        device_name: str,
    ) -> None:
        """Initialize single switch entity."""
        
        super().__init__(
            coordinator=coordinator,
            device_key=device_key,
            entity_key="switch",
            entity_name=device_name
        )
    
    async def _send_switch_command(self, turn_on: bool) -> bool:
        """Send switch command to single switch device."""
        try:
            if turn_on:
                op_code = TIS_OPCODES["LIGHT_ON"]
            else:
                op_code = TIS_OPCODES["LIGHT_OFF"]
            
            success = await self.async_send_command(op_code)
            
            if success:
                _LOGGER.debug(f"Switch {self.entity_id} turned {'on' if turn_on else 'off'}")
            else:
                _LOGGER.warning(f"Failed to turn {'on' if turn_on else 'off'} switch {self.entity_id}")
            
            return success
            
        except Exception as e:
            _LOGGER.error(f"Error sending switch command to {self.entity_id}: {e}")
            return False
    
    def _update_switch_state_from_data(self, device_state: Dict[str, Any]) -> None:
        """Update single switch state from device state data."""
        # Look for switch data in device state
        if "switches" in device_state:
            switches_data = device_state["switches"]
            if isinstance(switches_data, list) and switches_data:
                switch_data = switches_data[0]  # First (and only) switch
                if isinstance(switch_data, dict):
                    state = switch_data.get("state")
                    if state == "on":
                        self._is_on = True
                    elif state == "off":
                        self._is_on = False
                    # If state is "unknown", keep current state
        
        # Fallback: check for generic device state
        elif "state" in device_state:
            state = device_state["state"]
            if state == "on":
                self._is_on = True
            elif state == "off":
                self._is_on = False

class TISMultiGangSwitchEntity(TISMultiChannelEntity, SwitchEntity):
    """Multi-gang switch entity for TIS devices."""
    
    def __init__(
        self,
        coordinator: TISDataUpdateCoordinator,
        device_key: str,
        gang_index: int,
        device_name: str,
    ) -> None:
        """Initialize multi-gang switch entity."""
        
        # Get switch icon from entity definitions
        switch_def = ENTITY_DEFINITIONS.get("switch", {})
        
        super().__init__(
            coordinator=coordinator,
            device_key=device_key,
            channel_index=gang_index,
            entity_name=f"{device_name} Gang",  # Will become "Device Gang 1", "Device Gang 2", etc.
            entity_type="switch",
            icon=switch_def.get("icon"),
            device_class=switch_def.get("device_class")
        )
        
        # Switch state
        self._is_on = False
    
    @property
    def is_on(self) -> bool:
        """Return True if this gang is on."""
        return self._is_on
    
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn this gang on."""
        success = await self._send_gang_command(True)
        if success:
            self._is_on = True
            self.async_write_ha_state()
    
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn this gang off."""
        success = await self._send_gang_command(False)
        if success:
            self._is_on = False
            self.async_write_ha_state()
    
    async def _send_gang_command(self, turn_on: bool) -> bool:
        """Send command to specific gang of multi-gang switch."""
        try:
            # Build gang-specific command
            # For multi-gang switches, we need to send the gang index in additional data
            if turn_on:
                op_code = TIS_OPCODES["LIGHT_ON"]
            else:
                op_code = TIS_OPCODES["LIGHT_OFF"]
            
            # Add gang index to command (0-based for protocol, but we display as 1-based)
            additional_data = [self.channel_index]
            
            success = await self.async_send_command(op_code, additional_data)
            
            if success:
                _LOGGER.debug(
                    f"Multi-gang switch {self.entity_id} gang {self.channel_index + 1} "
                    f"turned {'on' if turn_on else 'off'}"
                )
            else:
                _LOGGER.warning(
                    f"Failed to turn {'on' if turn_on else 'off'} "
                    f"multi-gang switch {self.entity_id} gang {self.channel_index + 1}"
                )
            
            return success
            
        except Exception as e:
            _LOGGER.error(f"Error sending gang command to {self.entity_id}: {e}")
            return False
    
    def _update_from_coordinator_data(self) -> None:
        """Update gang state from coordinator data."""
        device_state = self.coordinator.get_device_state(self.device_key)
        if not device_state:
            return
        
        # Get data for this specific gang
        gang_data = self.get_channel_data("switches")
        if isinstance(gang_data, dict):
            state = gang_data.get("state")
            if state == "on":
                self._is_on = True
            elif state == "off":
                self._is_on = False
            # If state is "unknown", keep current state

class TISSceneSwitchEntity(TISSwitchEntity):
    """Scene switch entity for TIS scene controllers."""
    
    def __init__(
        self,
        coordinator: TISDataUpdateCoordinator,
        device_key: str,
        scene_index: int,
        device_name: str,
    ) -> None:
        """Initialize scene switch entity."""
        
        super().__init__(
            coordinator=coordinator,
            device_key=device_key,
            entity_key=f"scene_{scene_index}",
            entity_name=f"{device_name} Scene {scene_index + 1}"
        )
        
        self.scene_index = scene_index
        # Scene switches are typically momentary - they don't have persistent on/off state
        self._is_on = False
    
    @property
    def is_on(self) -> bool:
        """Scene switches are typically momentary, so always return False."""
        return False
    
    async def _send_switch_command(self, turn_on: bool) -> bool:
        """Send scene activation command."""
        try:
            # Scene switches typically only activate (turn_on), ignore turn_off
            if not turn_on:
                return True
            
            # Use generic device control with scene index
            op_code = TIS_OPCODES["DEVICE_ON"] 
            additional_data = [self.scene_index]
            
            success = await self.async_send_command(op_code, additional_data)
            
            if success:
                _LOGGER.info(f"Scene {self.scene_index + 1} activated on {self.entity_id}")
                # Scene activation is momentary, reset state after short delay
                self._is_on = False
                self.async_write_ha_state()
            
            return success
            
        except Exception as e:
            _LOGGER.error(f"Error activating scene on {self.entity_id}: {e}")
            return False
    
    def _update_switch_state_from_data(self, device_state: Dict[str, Any]) -> None:
        """Scene switches don't have persistent state."""
        # Scene switches are typically momentary, no persistent state to update
        self._is_on = False

class TISCurtainSwitchEntity(TISSwitchEntity):
    """Curtain switch entity for TIS curtain controllers."""
    
    def __init__(
        self,
        coordinator: TISDataUpdateCoordinator,
        device_key: str,
        device_name: str,
    ) -> None:
        """Initialize curtain switch entity."""
        
        super().__init__(
            coordinator=coordinator,
            device_key=device_key,
            entity_key="curtain",
            entity_name=f"{device_name} Curtain"
        )
        
        # Curtain position (0=closed, 1=open)
        self._curtain_position = 0
    
    @property
    def is_on(self) -> bool:
        """Return True if curtain is open."""
        return self._curtain_position > 0.5
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional curtain attributes."""
        attrs = super().extra_state_attributes
        attrs.update({
            "curtain_position": self._curtain_position,
            "curtain_state": "open" if self.is_on else "closed"
        })
        return attrs
    
    async def _send_switch_command(self, turn_on: bool) -> bool:
        """Send curtain control command."""
        try:
            # Use lighting control opcodes for curtain (they're typically similar)
            if turn_on:
                op_code = TIS_OPCODES["LIGHT_ON"]  # Open curtain
            else:
                op_code = TIS_OPCODES["LIGHT_OFF"]  # Close curtain
            
            success = await self.async_send_command(op_code)
            
            if success:
                # Update position immediately for responsiveness
                self._curtain_position = 1.0 if turn_on else 0.0
                _LOGGER.debug(f"Curtain {self.entity_id} {'opened' if turn_on else 'closed'}")
            
            return success
            
        except Exception as e:
            _LOGGER.error(f"Error controlling curtain {self.entity_id}: {e}")
            return False
    
    def _update_switch_state_from_data(self, device_state: Dict[str, Any]) -> None:
        """Update curtain state from device state data."""
        # Look for curtain-specific data
        if "curtain" in device_state:
            curtain_data = device_state["curtain"]
            if isinstance(curtain_data, dict):
                position = curtain_data.get("position")
                if position is not None:
                    self._curtain_position = float(position)
                
                state = curtain_data.get("state")
                if state == "open":
                    self._curtain_position = 1.0
                elif state == "closed":
                    self._curtain_position = 0.0
        
        # Fallback to generic switch data
        else:
            self._update_switch_state_from_data(device_state)
            if self._is_on:
                self._curtain_position = 1.0
            else:
                self._curtain_position = 0.0

# Factory function for creating appropriate switch entities
def create_switch_entity(
    coordinator: TISDataUpdateCoordinator,
    device_wrapper: TISDeviceWrapper,
    switch_index: int = 0
) -> TISSwitchEntity:
    """Create appropriate switch entity based on device type."""
    
    device_type_name = device_wrapper.device_type_name
    device_key = device_wrapper.device_key
    device_name = device_wrapper.tis_device.name
    
    # Get device capabilities to determine switch count
    capabilities = DEVICE_CAPABILITIES.get(device_type_name, [])
    switch_count = len([cap for cap in capabilities if cap == "switch"])
    
    if "scene" in device_type_name:
        return TISSceneSwitchEntity(
            coordinator=coordinator,
            device_key=device_key,
            scene_index=switch_index,
            device_name=device_name
        )
    elif "curtain" in device_type_name:
        return TISCurtainSwitchEntity(
            coordinator=coordinator,
            device_key=device_key,
            device_name=device_name
        )
    elif switch_count > 1:
        return TISMultiGangSwitchEntity(
            coordinator=coordinator,
            device_key=device_key,
            gang_index=switch_index,
            device_name=device_name
        )
    else:
        return TISSingleSwitchEntity(
            coordinator=coordinator,
            device_key=device_key,
            device_name=device_name
        )
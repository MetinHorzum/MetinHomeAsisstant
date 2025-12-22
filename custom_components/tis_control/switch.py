"""TIS Control Switch platform."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import TISConfigEntry

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TISConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up TIS Control switches from config entry."""
    api = entry.runtime_data.api
    mock_mode = entry.runtime_data.mock_mode
    
    switches = []
    
    try:
        # Get switch entities from API
        switch_entities = await api.get_entities(platform="switch")
        
        for switch_data in switch_entities:
            for switch_name, config in switch_data.items():
                switches.append(
                    TISSwitch(
                        api=api,
                        name=switch_name,
                        device_id=config["device_id"],
                        channel=list(config["channels"][0].keys())[0],
                        mock_mode=mock_mode
                    )
                )
        
        if switches:
            _LOGGER.info(f"TIS Control: {len(switches)} anahtar entity'si yüklendi")
            async_add_entities(switches)
        elif mock_mode:
            _LOGGER.info("TIS Control: Test modunda anahtar entity'si bulunamadı")
            
    except Exception as err:
        _LOGGER.error("Switch setup hatası: %s", err)


class TISSwitch(SwitchEntity):
    """TIS Control Switch Entity."""

    def __init__(
        self,
        api: Any,
        name: str,
        device_id: tuple,
        channel: str,
        mock_mode: bool = False
    ) -> None:
        """Initialize TIS switch."""
        self._api = api
        self._attr_name = name
        self._device_id = device_id
        self._channel = int(channel)
        self._mock_mode = mock_mode
        
        # Set unique ID
        self._attr_unique_id = f"tis_switch_{device_id[0]}_{device_id[1]}_{channel}"
        
        # Set default attributes
        self._attr_is_on = False
        
        if mock_mode:
            _LOGGER.debug(f"Test modu anahtar oluşturuldu: {name}")

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {("tis_control", f"{self._device_id[0]}_{self._device_id[1]}")},
            "name": f"TIS Device {self._device_id[0]:02X}{self._device_id[1]:02X}",
            "manufacturer": "TIS Control",
            "model": f"Device {self._device_id[0]:02X}-{self._device_id[1]:02X}",
            "via_device": ("tis_control", "bridge"),
        }

    @property 
    def available(self) -> bool:
        """Return True if entity is available."""
        return True  # Always available in mock mode

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the switch."""
        if self._mock_mode:
            # Mock implementation - just update state
            self._attr_is_on = True
            _LOGGER.info(f"Test modu: {self.name} açıldı")
        else:
            # Real implementation would go here
            try:
                # await self._api.send_switch_command(...)
                self._attr_is_on = True
            except Exception as err:
                _LOGGER.error("Anahtar açma hatası: %s", err)
        
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the switch."""
        if self._mock_mode:
            # Mock implementation
            self._attr_is_on = False
            _LOGGER.info(f"Test modu: {self.name} kapatıldı")
        else:
            # Real implementation would go here
            try:
                # await self._api.send_switch_command(...)
                self._attr_is_on = False
            except Exception as err:
                _LOGGER.error("Anahtar kapatma hatası: %s", err)
        
        self.async_write_ha_state()

    async def async_update(self) -> None:
        """Update the switch state."""
        if self._mock_mode:
            # In mock mode, don't try to fetch real data
            return
        
        try:
            # Real update implementation would go here
            # state = await self._api.get_switch_state(...)
            pass
        except Exception as err:
            _LOGGER.error("Anahtar durumu güncelleme hatası: %s", err)
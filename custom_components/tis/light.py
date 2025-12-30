from __future__ import annotations
from typing import Any
from homeassistant.components.light import LightEntity, ColorMode, ATTR_BRIGHTNESS
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import TisCoordinator

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    coordinator: TisCoordinator = hass.data[DOMAIN][entry.entry_id]
    added_lights = set()

    @callback
    def _update_entities():
        new_entities = []
        for dev_id, dev in coordinator.data.discovered.items():
            # RCU-24R20Z tipi: 32811
            if dev.device_type == 32811:
                for ch in range(1, 25): # 24 Kanal
                    uid = f"{dev_id}_ch_{ch}"
                    if uid not in added_lights:
                        new_entities.append(TisLight(coordinator, dev, ch))
                        added_lights.add(uid)
        if new_entities:
            async_add_entities(new_entities)

    coordinator.async_add_listener(_update_entities)
    _update_entities()

class TisLight(LightEntity):
    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}

    def __init__(self, coordinator: TisCoordinator, device_info, channel: int):
        self.coordinator = coordinator
        self._device = device_info
        self._channel = channel
        self._attr_unique_id = f"{device_info.unique_id}_ch_{channel}"
        self._attr_name = f"{device_info.name or 'RCU24'} Ch{channel}"
        self._is_on = False
        self._brightness = 255

    @property
    def is_on(self) -> bool: return self._is_on

    @property
    def brightness(self) -> int: return self._brightness

    async def async_turn_on(self, **kwargs: Any) -> None:
        brightness = kwargs.get(ATTR_BRIGHTNESS, 255)
        level = int((brightness / 255) * 100) # TIS 0-100 arası çalışır
        
        # Opcode 0x0031: Single Channel Control
        # Payload: [Kanal, Yüzde, GecikmeH, GecikmeL]
        await self.coordinator.client.async_send_command(
            self._device.src_sub, self._device.src_dev, 0x0031, [self._channel, level, 0, 0]
        )
        self._is_on = True
        self._brightness = brightness
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.client.async_send_command(
            self._device.src_sub, self._device.src_dev, 0x0031, [self._channel, 0, 0, 0]
        )
        self._is_on = False
        self.async_write_ha_state()
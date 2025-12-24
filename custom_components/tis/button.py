from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([TisScanButton(coordinator)], True)


class TisScanButton(ButtonEntity):
    _attr_name = "TIS Cihazları Tara"
    _attr_has_entity_name = True
    _attr_unique_id = "tis_scan_button"
    _attr_icon = "mdi:magnify-scan"

    def __init__(self, coordinator):
        self.coordinator = coordinator

    async def async_press(self) -> None:
        await self.coordinator.async_discover(show_notification=True)

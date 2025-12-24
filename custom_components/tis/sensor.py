import time

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            TisDiscoveredCountSensor(coordinator),
            TisSecondsSinceLastPacketSensor(coordinator),
        ],
        True,
    )


class _BaseTisSensor(SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator):
        self.coordinator = coordinator

    async def async_update(self):
        # Manual refresh triggers discovery to make debugging easy
        await self.coordinator.async_discover()


class TisDiscoveredCountSensor(_BaseTisSensor):
    _attr_name = "Discovered devices"
    _attr_unique_id = "tis_discovered_count"

    @property
    def native_value(self):
        return len(self.coordinator.data.discovered)


class TisSecondsSinceLastPacketSensor(_BaseTisSensor):
    _attr_name = "Seconds since last packet"
    _attr_unique_id = "tis_seconds_since_last_packet"
    _attr_native_unit_of_measurement = "s"

    @property
    def native_value(self):
        ts = self.coordinator.data.last_rx_ts
        if ts is None:
            return None
        return round(time.time() - ts, 1)

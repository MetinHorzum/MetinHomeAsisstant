from __future__ import annotations

import time

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import TisCoordinator, TisDeviceInfo


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: TisCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Do one discovery scan at setup so devices show up immediately
    await coordinator.async_discover()

    entities: list[SensorEntity] = [
        TisDiscoveredCountSensor(coordinator),
        TisSecondsSinceLastPacketSensor(coordinator),
    ]

    for dev in coordinator.data.discovered.values():
        entities.append(TisDeviceLastSeenSecondsSensor(coordinator, dev))

    async_add_entities(entities, True)


class _BaseTisSensor(SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: TisCoordinator):
        self.coordinator = coordinator

    async def async_update(self) -> None:
        # For now, trigger a discovery scan when HA asks for an update.
        # Later we can split "scan" and "telemetry" opcodes.
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

    @property
    def native_value(self):
        ts = self.coordinator.data.last_rx_ts
        if ts is None:
            return None
        return int(time.time() - ts)


class TisDeviceLastSeenSecondsSensor(_BaseTisSensor):
    _attr_icon = "mdi:lan-connect"

    def __init__(self, coordinator: TisCoordinator, dev: TisDeviceInfo):
        super().__init__(coordinator)
        self.dev = dev
        # Unique per RS485 device behind the gateway
        self._attr_unique_id = f"tis_{dev.unique_id}_last_seen"
        self._attr_name = dev.name or f"TIS Device {dev.device_type:04X} last seen"

    @property
    def device_info(self):
        # This makes the device appear in HA's "Devices" list
        return {
            "identifiers": {(DOMAIN, self.dev.unique_id)},
            "name": self.dev.name or f"TIS {self.dev.device_type:04X}",
            "manufacturer": "TIS",
            "model": f"{self.dev.device_type:04X}",
            "via_device": (DOMAIN, self.coordinator.client.host),
        }

    @property
    def native_value(self):
        # Refresh current device info from coordinator data (it may have been updated)
        dev = self.coordinator.data.discovered.get(self.dev.unique_id)
        if not dev:
            return None
        return int(time.time() - dev.last_seen)

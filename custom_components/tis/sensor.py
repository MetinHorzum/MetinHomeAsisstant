from __future__ import annotations

import time
from typing import Any, Dict, List

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import TisDeviceInfo, TisCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: TisCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([TisDiscoveryListSensor(coordinator)], True)


class TisDiscoveryListSensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Discovery devices"
    _attr_unique_id = "tis_discovery_devices"
    _attr_icon = "mdi:radar"

    def __init__(self, coordinator: TisCoordinator):
        self.coordinator = coordinator

    async def async_update(self) -> None:
        await self.coordinator.async_request_refresh()

    @property
    def native_value(self) -> int:
        return len(self.coordinator.data.discovered or {})

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        devices = self._devices_as_list(self.coordinator.data.discovered or {})
        return {
            "last_rx_age_s": self._last_rx_age(),
            "devices": devices,
        }

    def _last_rx_age(self):
        ts = self.coordinator.data.last_rx_ts
        if ts is None:
            return None
        return round(time.time() - ts, 1)

    def _devices_as_list(self, discovered: Dict[str, TisDeviceInfo]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        now = time.time()

        def _key(item):
            d = item[1]
            return (d.gw_ip, d.src_sub, d.src_dev)

        for _, dev in sorted(discovered.items(), key=_key):
            out.append(
                {
                    "gw_ip": dev.gw_ip,
                    "src": dev.src_str,
                    "name": dev.name,
                    "device_type": dev.device_type,
                    "model": dev.device_model,
                    "last_seen_age_s": round(now - float(dev.last_seen or 0.0), 1),
                    "opcodes_seen": sorted(list(dev.opcodes_seen)),
                    "unique_id": dev.unique_id,
                }
            )
        return out

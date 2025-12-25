from __future__ import annotations

import time
from typing import Dict, Set

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, DEVICE_TYPES
from .coordinator import TisDeviceInfo


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]

    added: Set[str] = set()

    # debug sensörler
    entities = [
        TisDiscoveredCountSensor(coordinator),
        TisSecondsSinceLastPacketSensor(coordinator),
    ]

    # ilk açılışta elde olan discovered cihazları ekle
    for dev_id, dev in (coordinator.data.discovered or {}).items():
        entities.append(TisDiscoveredDeviceSensor(coordinator, entry.entry_id, dev))
        added.add(dev_id)

    async_add_entities(entities, True)

    # sonradan keşfedilen cihazları dinleyip ekle
    @callback
    def _maybe_add_new_devices() -> None:
        new_entities = []
        for dev_id, dev in (coordinator.data.discovered or {}).items():
            if dev_id in added:
                continue
            new_entities.append(TisDiscoveredDeviceSensor(coordinator, entry.entry_id, dev))
            added.add(dev_id)
        if new_entities:
            async_add_entities(new_entities, True)

    coordinator.async_add_listener(_maybe_add_new_devices)


class _BaseTisSensor(SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator):
        self.coordinator = coordinator

    async def async_update(self):
        # Manuel refresh (UI'dan güncelle) discovery'yi tekrar koşturur
        await self.coordinator.async_discover()


class TisDiscoveredCountSensor(_BaseTisSensor):
    _attr_name = "Discovered devices"
    _attr_unique_id = "tis_discovered_count"

    @property
    def native_value(self):
        return len(self.coordinator.data.discovered or {})


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


class TisDiscoveredDeviceSensor(_BaseTisSensor):
    """Her discovered cihaz için 1 adet entity.

    - Entity state: online/offline
    - Attributes: GW IP, SRC, type, opcodes, last_seen...
    - device_info: HA 'Cihazlar' sekmesinde ayrı cihaz olarak görünür
    """

    _attr_icon = "mdi:lan-connect"

    def __init__(self, coordinator, entry_id: str, dev: TisDeviceInfo):
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._dev_id = dev.unique_id
        self._attr_unique_id = f"tis_{entry_id}_{dev.unique_id}"

        # İsim: varsa cihaz adı, yoksa src
        nice_name = dev.name.strip() if dev.name else dev.src_str
        self._attr_name = f"{nice_name}"

    @property
    def _dev(self) -> TisDeviceInfo | None:
        return (self.coordinator.data.discovered or {}).get(self._dev_id)

    @property
    def native_value(self):
        dev = self._dev
        if not dev:
            return "unknown"
        # 30 sn içinde görüldüyse online
        age = time.time() - float(dev.last_seen or 0.0)
        return "online" if age <= 30 else "offline"

    @property
    def extra_state_attributes(self) -> Dict:
        dev = self._dev
        if not dev:
            return {}
        model = DEVICE_TYPES.get(dev.device_type) if dev.device_type is not None else None
        return {
            "gw_ip": dev.gw_ip,
            "src": dev.src_str,
            "name": dev.name,
            "device_type": dev.device_type,
            "device_type_hex": dev.device_type_hex,
            "device_model": model,
            "last_seen_age_s": round(time.time() - float(dev.last_seen or 0.0), 1),
            "opcodes_seen": sorted(list(dev.opcodes_seen)),
        }

    @property
    def device_info(self):
        """Bu entity'yi bir 'cihaz'a bağla (Devices sekmesi için)."""
        dev = self._dev
        if not dev:
            return {
                "identifiers": {(DOMAIN, self._dev_id)},
                "name": self._attr_name,
            }

        model = DEVICE_TYPES.get(dev.device_type) if dev.device_type is not None else None
        return {
            "identifiers": {(DOMAIN, dev.unique_id)},
            "name": dev.name.strip() or f"TIS {dev.src_str}",
            "manufacturer": "TIS",
            "model": model or dev.device_type_hex or "SMARTCLOUD",
            "suggested_area": "TIS",
        }

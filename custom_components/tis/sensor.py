from __future__ import annotations

import time
from typing import Dict, Set, List

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, DEVICE_TYPES
from .coordinator import TisCoordinator, TisDeviceInfo


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: TisCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = [
        TisDiscoveredCountSensor(coordinator),
        TisSecondsSinceLastPacketSensor(coordinator),
    ]

    # existing discovered devices -> add availability + channels
    known: Set[str] = set()
    for uid, dev in (coordinator.data.discovered or {}).items():
        entities.append(TisDeviceAvailabilitySensor(coordinator, uid))
        known.add(uid)
        entities.extend(_build_channel_entities(coordinator, dev))

    async_add_entities(entities)

    @callback
    def _maybe_add_new() -> None:
        new_entities: list[SensorEntity] = []
        for uid, dev in (coordinator.data.discovered or {}).items():
            if uid not in known:
                known.add(uid)
                new_entities.append(TisDeviceAvailabilitySensor(coordinator, uid))
                new_entities.extend(_build_channel_entities(coordinator, dev))
            else:
                # device exists: maybe channel list expanded later (0x0005 arrives later)
                new_entities.extend(_build_missing_channel_entities(coordinator, dev))
        if new_entities:
            async_add_entities(new_entities)

    coordinator.async_add_listener(_maybe_add_new)


def _build_channel_entities(coordinator: TisCoordinator, dev: TisDeviceInfo) -> list[SensorEntity]:
    ents: list[SensorEntity] = []
    qty = dev.rcu_qty or (len(dev.rcu_types) if dev.rcu_types else 0)
    for ch in range(qty):
        ents.append(TisChannelTypeSensor(coordinator, dev.unique_id, ch))
        ents.append(TisChannelStateSensor(coordinator, dev.unique_id, ch))
        ents.append(TisChannelLevelSensor(coordinator, dev.unique_id, ch))
    return ents


def _build_missing_channel_entities(coordinator: TisCoordinator, dev: TisDeviceInfo) -> list[SensorEntity]:
    """If types packet arrives later and increases qty, add missing channel entities."""
    ents: list[SensorEntity] = []
    qty = dev.rcu_qty or (len(dev.rcu_types) if dev.rcu_types else 0)
    if qty <= 0:
        return ents

    # We cannot easily check entity registry here without extra HA helpers,
    # so we create entities only when qty increases by tracking max seen per device in coordinator object.
    # Minimal approach: store a private attribute on coordinator.
    if not hasattr(coordinator, "_tis_max_qty"):
        setattr(coordinator, "_tis_max_qty", {})  # type: ignore[attr-defined]
    max_map: Dict[str, int] = getattr(coordinator, "_tis_max_qty")  # type: ignore[attr-defined]

    prev = max_map.get(dev.unique_id, 0)
    if qty > prev:
        for ch in range(prev, qty):
            ents.append(TisChannelTypeSensor(coordinator, dev.unique_id, ch))
            ents.append(TisChannelStateSensor(coordinator, dev.unique_id, ch))
            ents.append(TisChannelLevelSensor(coordinator, dev.unique_id, ch))
        max_map[dev.unique_id] = qty
    return ents


class _BaseTisSensor(SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: TisCoordinator):
        self.coordinator = coordinator

    async def async_update(self):
        # manual update triggers discovery again
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


class TisDeviceAvailabilitySensor(_BaseTisSensor):
    """One entity per device: online/offline."""

    def __init__(self, coordinator: TisCoordinator, dev_id: str):
        super().__init__(coordinator)
        self._dev_id = dev_id
        self._attr_unique_id = f"tis_{dev_id}_availability"
        self._attr_name = "Availability"

    @property
    def native_value(self):
        dev = (self.coordinator.data.discovered or {}).get(self._dev_id)
        if not dev:
            return "unknown"
        age = time.time() - dev.last_seen
        return "online" if age < 30 else "offline"

    @property
    def extra_state_attributes(self):
        dev = (self.coordinator.data.discovered or {}).get(self._dev_id)
        if not dev:
            return None
        model = DEVICE_TYPES.get(dev.device_type) if dev.device_type is not None else None
        return {
            "gw_ip": dev.gw_ip,
            "src": dev.src_str,
            "name": dev.name,
            "device_type": dev.device_type_hex,
            "device_model": model,
            "last_seen_age_s": round(time.time() - dev.last_seen, 1),
            "opcodes_seen": sorted(list(dev.opcodes_seen)),
            "rcu_qty": dev.rcu_qty,
            "rcu_kind": dev.rcu_kind,
            "rcu_types_len": len(dev.rcu_types),
            "rcu_states_len": len(dev.rcu_states),
            "ch_levels_len": len(dev.ch_levels),
        }

    @property
    def device_info(self):
        dev = (self.coordinator.data.discovered or {}).get(self._dev_id)
        if not dev:
            return {"identifiers": {(DOMAIN, self._dev_id)}, "name": self._dev_id}

        model = DEVICE_TYPES.get(dev.device_type) if dev.device_type is not None else None
        return {
            "identifiers": {(DOMAIN, dev.unique_id)},
            "name": dev.name.strip() or f"TIS {dev.src_str}",
            "manufacturer": "TIS",
            "model": model or dev.device_type_hex or "SMARTCLOUD",
            "suggested_area": "TIS",
        }


class _BaseChannelSensor(_BaseTisSensor):
    """Base for per-channel sensors."""

    def __init__(self, coordinator: TisCoordinator, dev_id: str, ch: int):
        super().__init__(coordinator)
        self._dev_id = dev_id
        self._ch = ch

    @property
    def _dev(self) -> TisDeviceInfo | None:
        return (self.coordinator.data.discovered or {}).get(self._dev_id)

    @property
    def device_info(self):
        dev = self._dev
        if not dev:
            return {"identifiers": {(DOMAIN, self._dev_id)}, "name": self._dev_id}
        model = DEVICE_TYPES.get(dev.device_type) if dev.device_type is not None else None
        return {
            "identifiers": {(DOMAIN, dev.unique_id)},
            "name": dev.name.strip() or f"TIS {dev.src_str}",
            "manufacturer": "TIS",
            "model": model or dev.device_type_hex or "SMARTCLOUD",
        }

    @property
    def extra_state_attributes(self):
        dev = self._dev
        if not dev:
            return None
        return {
            "gw_ip": dev.gw_ip,
            "src": dev.src_str,
            "channel": self._ch,
            "last_seen_age_s": round(time.time() - dev.last_seen, 1),
        }


class TisChannelTypeSensor(_BaseChannelSensor):
    """RCU channel type from 0x0005."""

    def __init__(self, coordinator: TisCoordinator, dev_id: str, ch: int):
        super().__init__(coordinator, dev_id, ch)
        self._attr_unique_id = f"tis_{dev_id}_ch{ch+1}_type"
        self._attr_name = f"CH{ch+1} Type"

    @property
    def native_value(self):
        dev = self._dev
        if not dev or self._ch >= len(dev.rcu_types):
            return None
        # keep raw int (reverse engineering safe)
        return int(dev.rcu_types[self._ch])


class TisChannelStateSensor(_BaseChannelSensor):
    """RCU channel state bytes from 0x2025."""

    def __init__(self, coordinator: TisCoordinator, dev_id: str, ch: int):
        super().__init__(coordinator, dev_id, ch)
        self._attr_unique_id = f"tis_{dev_id}_ch{ch+1}_state"
        self._attr_name = f"CH{ch+1} State"

    @property
    def native_value(self):
        dev = self._dev
        if not dev or self._ch >= len(dev.rcu_states):
            return None
        return int(dev.rcu_states[self._ch])


class TisChannelLevelSensor(_BaseChannelSensor):
    """Channel levels from 0x0034 (0-100). Useful for dimmers too if it matches."""

    def __init__(self, coordinator: TisCoordinator, dev_id: str, ch: int):
        super().__init__(coordinator, dev_id, ch)
        self._attr_unique_id = f"tis_{dev_id}_ch{ch+1}_level"
        self._attr_name = f"CH{ch+1} Level"

    @property
    def native_value(self):
        dev = self._dev
        if not dev or self._ch >= len(dev.ch_levels):
            return None
        return int(dev.ch_levels[self._ch])

from __future__ import annotations

import logging
from typing import Set

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, RCU_DEVICE_TYPE
from .coordinator import TisCoordinator, TisDeviceInfo

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: TisCoordinator = hass.data[DOMAIN][entry.entry_id]

    added: Set[str] = set()

    def _add_for_current_state() -> None:
        new_entities: list[BinarySensorEntity] = []
        for dev in coordinator.data.discovered.values():
            if dev.device_type != RCU_DEVICE_TYPE:
                continue

            # Digital inputs (bitfield decoded from 0xD219)
            for idx in range(1, len(dev.rcu_di_bits) + 1):
                uid = f"{dev.unique_id}-rcu-di-{idx}"
                if uid in added:
                    continue
                added.add(uid)
                new_entities.append(TisRcuDigitalInput(coordinator, dev.unique_id, idx))

            # If the device ever reports channel types with input channels, expose them too.
            if dev.rcu_types:
                qty = len(dev.rcu_types)
                for ch in range(1, qty + 1):
                    if dev.rcu_types[ch - 1] != 0x02:
                        continue
                    uid = f"{dev.unique_id}-rcu-in-{ch}"
                    if uid in added:
                        continue
                    added.add(uid)
                    new_entities.append(TisRcuInputChannel(coordinator, dev.unique_id, ch))

        if new_entities:
            async_add_entities(new_entities)

    _add_for_current_state()
    coordinator.async_add_listener(_add_for_current_state)


class _BaseRcuBinary(CoordinatorEntity[TisCoordinator], BinarySensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: TisCoordinator, device_uid: str) -> None:
        super().__init__(coordinator)
        self._device_uid = device_uid

    @property
    def _dev(self) -> TisDeviceInfo | None:
        return self.coordinator.data.discovered.get(self._device_uid)

    @property
    def device_info(self):
        dev = self._dev
        if not dev:
            return None
        return {
            "identifiers": {(DOMAIN, dev.unique_id)},
            "name": dev.name or f"RCU {dev.src_str}",
            "manufacturer": "TIS",
            "model": dev.device_model,
        }


class TisRcuDigitalInput(_BaseRcuBinary):
    """RCU 'mechanical switch' digital input as binary_sensor."""

    _attr_icon = "mdi:gesture-tap"

    def __init__(self, coordinator: TisCoordinator, device_uid: str, di_index: int) -> None:
        super().__init__(coordinator, device_uid)
        self._di_index = di_index
        self._attr_unique_id = f"{device_uid}-rcu-di-{di_index}"

    @property
    def name(self) -> str:
        return f"DI {self._di_index}"

    @property
    def is_on(self) -> bool | None:
        dev = self._dev
        if not dev:
            return None
        if self._di_index - 1 >= len(dev.rcu_di_bits):
            return None
        return bool(dev.rcu_di_bits[self._di_index - 1])


class TisRcuInputChannel(_BaseRcuBinary):
    """If RCU reports per-channel INPUT types (0x02), expose them here."""

    _attr_icon = "mdi:circle-slice-8"

    def __init__(self, coordinator: TisCoordinator, device_uid: str, ch: int) -> None:
        super().__init__(coordinator, device_uid)
        self._ch = ch
        self._attr_unique_id = f"{device_uid}-rcu-in-{ch}"

    @property
    def name(self) -> str:
        dev = self._dev
        if not dev:
            return f"IN {self._ch}"
        return dev.rcu_names.get(self._ch, f"IN {self._ch}")

    @property
    def is_on(self) -> bool | None:
        dev = self._dev
        if not dev:
            return None
        if self._ch - 1 >= len(dev.rcu_states):
            return None
        return bool(dev.rcu_states[self._ch - 1])

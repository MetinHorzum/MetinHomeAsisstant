from __future__ import annotations

import logging
from typing import Set

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
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
        new_entities: list[SwitchEntity] = []
        for dev in coordinator.data.discovered.values():
            if dev.device_type != RCU_DEVICE_TYPE:
                continue

            qty = len(dev.rcu_types) or len(dev.rcu_states)
            if qty <= 0:
                continue

            for ch in range(1, qty + 1):
                # If types exist, only expose outputs.
                if dev.rcu_types and ch - 1 < len(dev.rcu_types):
                    if dev.rcu_types[ch - 1] != 0x01:
                        continue

                uid = f"{dev.unique_id}-rcu-out-{ch}"
                if uid in added:
                    continue
                added.add(uid)
                new_entities.append(TisRcuOutputSwitch(coordinator, dev.unique_id, ch))

        if new_entities:
            async_add_entities(new_entities)

    _add_for_current_state()
    coordinator.async_add_listener(_add_for_current_state)


class TisRcuOutputSwitch(CoordinatorEntity[TisCoordinator], SwitchEntity):
    """Read-only switch for an RCU output channel.

    NOTE: We intentionally do NOT implement turn_on/turn_off until the correct
    control opcode/payload is captured. The entity still shows live state.
    """

    _attr_has_entity_name = True
    _attr_icon = "mdi:toggle-switch"

    def __init__(self, coordinator: TisCoordinator, device_uid: str, channel: int) -> None:
        super().__init__(coordinator)
        self._device_uid = device_uid
        self._channel = channel
        self._attr_unique_id = f"{device_uid}-rcu-out-{channel}"

    @property
    def _dev(self) -> TisDeviceInfo | None:
        return self.coordinator.data.discovered.get(self._device_uid)

    @property
    def name(self) -> str:
        dev = self._dev
        if not dev:
            return f"RCU CH {self._channel}"
        return dev.rcu_names.get(self._channel, f"CH {self._channel}")

    @property
    def is_on(self) -> bool | None:
        dev = self._dev
        if not dev:
            return None
        if self._channel - 1 >= len(dev.rcu_states):
            return None
        return bool(dev.rcu_states[self._channel - 1])

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

    async def async_turn_on(self, **kwargs) -> None:
        raise HomeAssistantError(
            "RCU output kontrolü henüz eklenmedi (set opcode/payload yakalanınca eklenecek)."
        )

    async def async_turn_off(self, **kwargs) -> None:
        raise HomeAssistantError(
            "RCU output kontrolü henüz eklenmedi (set opcode/payload yakalanınca eklenecek)."
        )

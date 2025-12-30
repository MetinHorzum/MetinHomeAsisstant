from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, RCU_STATE_RESP
from .coordinator import TisCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: TisCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SwitchEntity] = []

    for dev in coordinator.data.discovered.values():
        if dev.device_type == 0x802B:
            label = dev.name or f"RCU {dev.src_str}"
            for ch in range(1, 25):
                entities.append(TisRcuOutputSwitch(coordinator, dev.src_sub, dev.src_dev, ch, label))

    if entities:
        async_add_entities(entities, True)


class TisRcuOutputSwitch(SwitchEntity):
    _attr_icon = "mdi:toggle-switch"

    def __init__(self, coordinator: TisCoordinator, sub: int, dev: int, ch: int, label: str):
        self.coordinator = coordinator
        self.sub = sub
        self.dev = dev
        self.ch = ch
        self._attr_has_entity_name = True
        self._attr_name = f"{label} CH{ch}"
        self._attr_unique_id = f"tis_rcu_{sub}_{dev}_out_{ch}"

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, f"rcu_{self.sub}_{self.dev}")},
            "name": f"TIS RCU {self.sub}.{self.dev}",
            "manufacturer": "TIS",
            "model": "RCU",
        }

    async def async_update(self) -> None:
        await self.coordinator.async_request_refresh()

    @property
    def is_on(self) -> bool | None:
        payload = self.coordinator.data.payloads.get((self.sub, self.dev, RCU_STATE_RESP))
        if not payload or len(payload) < self.ch:
            return None
        v = payload[self.ch - 1]
        return v in (1, 100)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.client.rcu_set_output(self.sub, self.dev, self.ch, True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.client.rcu_set_output(self.sub, self.dev, self.ch, False)
        await self.coordinator.async_request_refresh()

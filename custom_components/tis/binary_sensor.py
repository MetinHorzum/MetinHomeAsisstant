from __future__ import annotations

from typing import Any, List

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, RCU_DI_RESP
from .coordinator import TisCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: TisCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[BinarySensorEntity] = []

    for dev in coordinator.data.discovered.values():
        if dev.device_type == 0x802B:
            label = dev.name or f"RCU {dev.src_str}"
            for di in range(1, 21):
                entities.append(TisRcuDigitalInput(coordinator, dev.src_sub, dev.src_dev, di, label))

    if entities:
        async_add_entities(entities, True)


def _bits_from_bytes(data: bytes) -> List[int]:
    bits: List[int] = []
    for b in data:
        for i in range(8):
            bits.append((b >> i) & 1)  # LSB-first
    return bits


class TisRcuDigitalInput(BinarySensorEntity):
    _attr_icon = "mdi:electric-switch"

    def __init__(self, coordinator: TisCoordinator, sub: int, dev: int, di: int, label: str):
        self.coordinator = coordinator
        self.sub = sub
        self.dev = dev
        self.di = di
        self._attr_has_entity_name = True
        self._attr_name = f"{label} DI{di}"
        self._attr_unique_id = f"tis_rcu_{sub}_{dev}_di_{di}"

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
        payload = self.coordinator.data.payloads.get((self.sub, self.dev, RCU_DI_RESP))
        if not payload:
            return None

        data = payload
        if len(payload) >= 3 and payload[0] == 0x0A:
            data = payload[2:]

        bits = _bits_from_bytes(data)
        idx = self.di - 1
        if idx >= len(bits):
            return None
        return bits[idx] == 1

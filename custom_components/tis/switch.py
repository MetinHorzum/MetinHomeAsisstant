from __future__ import annotations

from typing import Any, Dict, List

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DEVICE_TYPES, DOMAIN, SIGNAL_TIS_UPDATE
from .coordinator import TisCoordinator, TisDeviceInfo


def _is_rcu(device: TisDeviceInfo) -> bool:
    if device.device_type is None:
        return False
    model = DEVICE_TYPES.get(device.device_type, "")
    return model.startswith("RCU")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: TisCoordinator = hass.data[DOMAIN][entry.entry_id]

    created: set[str] = set()

    def build_for_device(dev: TisDeviceInfo) -> List[SwitchEntity]:
        if not _is_rcu(dev):
            return []
        if not dev.channel_types:
            return []
        entities: List[SwitchEntity] = []
        for ch, ch_type in enumerate(dev.channel_types, start=1):
            # Per tester: 0x01 = Output, 0x02 = Input
            if ch_type == 0x01:
                ent = TisRcuOutputSwitch(coordinator, dev.unique_id, ch)
                if ent.unique_id not in created:
                    created.add(ent.unique_id)
                    entities.append(ent)
        return entities

    # initial add
    initial: List[SwitchEntity] = []
    for dev in coordinator.client.state.discovered.values():
        initial.extend(build_for_device(dev))
    if initial:
        async_add_entities(initial)

    # dynamic add when new packets arrive and types become available
    def _on_update(unique_id: str) -> None:
        dev = coordinator.client.state.discovered.get(unique_id)
        if not dev:
            return
        new_entities = build_for_device(dev)
        if new_entities:
            async_add_entities(new_entities)

    async_dispatcher_connect(hass, SIGNAL_TIS_UPDATE, _on_update)


class TisRcuOutputSwitch(SwitchEntity):
    _attr_icon = "mdi:toggle-switch"

    def __init__(self, coordinator: TisCoordinator, device_unique_id: str, channel: int) -> None:
        self._coordinator = coordinator
        self._device_unique_id = device_unique_id
        self._channel = channel

        self._attr_unique_id = f"{device_unique_id}-rcu-out-{channel}"
        self._attr_name = f"TIS RCU OUT {channel}"

    def _device(self) -> TisDeviceInfo | None:
        return self._coordinator.client.state.discovered.get(self._device_unique_id)

    @property
    def available(self) -> bool:
        return self._device() is not None

    @property
    def is_on(self) -> bool | None:
        dev = self._device()
        if not dev:
            return None
        if len(dev.channel_states) >= self._channel:
            return bool(dev.channel_states[self._channel - 1])
        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        dev = self._device()
        if not dev:
            return
        await self._coordinator.client.send_set_channel(dev, self._channel, 100, ramp_seconds=0)

        # optimistic update
        if len(dev.channel_states) < self._channel:
            dev.channel_states.extend([0] * (self._channel - len(dev.channel_states)))
        dev.channel_states[self._channel - 1] = 1
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        dev = self._device()
        if not dev:
            return
        await self._coordinator.client.send_set_channel(dev, self._channel, 0, ramp_seconds=0)

        if len(dev.channel_states) < self._channel:
            dev.channel_states.extend([0] * (self._channel - len(dev.channel_states)))
        dev.channel_states[self._channel - 1] = 0
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        dev = self._device()
        attrs: Dict[str, Any] = {"channel": self._channel}
        if dev:
            dt = dev.device_type
            attrs.update(
                {
                    "gw_ip": dev.gw_ip,
                    "src": f"{dev.src_sub}.{dev.src_dev}",
                    "device_type": f"0x{dt:04X}" if dt is not None else None,
                    "device_model": DEVICE_TYPES.get(dt, "Unknown") if dt is not None else "Unknown",
                }
            )
        return attrs

    @property
    def device_info(self) -> Dict[str, Any]:
        dev = self._device()
        if not dev:
            return {"identifiers": {(DOMAIN, self._device_unique_id)}}

        dt = dev.device_type or 0
        model = DEVICE_TYPES.get(dt, f"0x{dt:04X}")
        return {
            "identifiers": {(DOMAIN, self._device_unique_id)},
            "name": dev.name or f"TIS {self._device_unique_id}",
            "manufacturer": "TIS",
            "model": model,
        }

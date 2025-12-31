from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DEVICE_TYPES, DOMAIN, SIGNAL_TIS_UPDATE
from .coordinator import TisCoordinator, TisDeviceInfo


def _is_rcu(dev: TisDeviceInfo) -> bool:
    """Best-effort detection of an RCU device."""
    dt = dev.device_type
    if dt is not None:
        model = DEVICE_TYPES.get(dt, "")
        if model.startswith("RCU"):
            return True

    name = (dev.name or "").upper()
    if "RCU" in name:
        return True

    seen = set(getattr(dev, "opcodes_seen", []) or [])
    if {0x2025, 0x0005, 0x0034, 0x0033, 0x0031, 0x0032}.intersection(seen):
        return True

    states = getattr(dev, "channel_states", [])
    if isinstance(states, list) and len(states) >= 20:
        return True

    return False


def _rcu_layout(dev: TisDeviceInfo) -> Tuple[int, int]:
    model = DEVICE_TYPES.get(dev.device_type or 0, "")
    if model.startswith("RCU24"):
        return 24, 20

    # If we already saw a long state vector, assume the common 24/20 layout.
    states = getattr(dev, "channel_states", [])
    if isinstance(states, list) and len(states) >= 44:
        return 24, 20

    return 0, 0


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: TisCoordinator = hass.data[DOMAIN][entry.entry_id]
    created: set[str] = set()

    def build(dev: TisDeviceInfo) -> List[BinarySensorEntity]:
        if not _is_rcu(dev):
            return []

        ents: List[BinarySensorEntity] = []
        # Preferred: use channel_types (0x0005)
        if getattr(dev, "channel_types", None):
            for ch, t in enumerate(dev.channel_types, start=1):
                if t == 0x02:
                    e = TisRcuInputBinarySensor(coordinator, dev.unique_id, physical_channel=ch)
                    if e.unique_id not in created:
                        created.add(e.unique_id)
                        ents.append(e)
            return ents

        # Fallback for RCU24: outputs first, then inputs
        outs, ins = _rcu_layout(dev)
        if outs and ins:
            base = outs + 1
            for i in range(1, ins + 1):
                physical = base + (i - 1)
                e = TisRcuInputBinarySensor(coordinator, dev.unique_id, physical_channel=physical, logical_input=i)
                if e.unique_id not in created:
                    created.add(e.unique_id)
                    ents.append(e)
        return ents

    initial: List[BinarySensorEntity] = []
    for dev in coordinator.client.state.discovered.values():
        initial.extend(build(dev))
    if initial:
        async_add_entities(initial)

    def _on_update(unique_id: str) -> None:
        dev = coordinator.client.state.discovered.get(unique_id)
        if not dev:
            return
        new = build(dev)
        if new:
            async_add_entities(new)

    async_dispatcher_connect(hass, SIGNAL_TIS_UPDATE, _on_update)


class TisRcuInputBinarySensor(BinarySensorEntity):
    _attr_icon = "mdi:ray-vertex"

    def __init__(self, coordinator: TisCoordinator, device_unique_id: str, physical_channel: int, logical_input: Optional[int] = None) -> None:
        self._coordinator = coordinator
        self._device_unique_id = device_unique_id
        self._physical_channel = physical_channel
        self._logical_input = logical_input
        suffix = logical_input if logical_input is not None else physical_channel
        self._attr_unique_id = f"{device_unique_id}-rcu-in-{suffix}"
        self._attr_name = f"TIS RCU IN {suffix}"

    def _device(self) -> Optional[TisDeviceInfo]:
        return self._coordinator.client.state.discovered.get(self._device_unique_id)

    @property
    def available(self) -> bool:
        return self._device() is not None

    @property
    def is_on(self) -> Optional[bool]:
        dev = self._device()
        if not dev:
            return None
        states = getattr(dev, "channel_states", [])
        idx = self._physical_channel - 1
        if 0 <= idx < len(states):
            return bool(states[idx])
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return {"physical_channel": self._physical_channel, "logical_input": self._logical_input}

    @property
    def device_info(self) -> Dict[str, Any]:
        return {"identifiers": {(DOMAIN, self._device_unique_id)}}

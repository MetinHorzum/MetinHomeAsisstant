from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN
from .coordinator import TisCoordinator, TisUdpClient

PLATFORMS: list[str] = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    host = entry.data["host"]
    port = entry.data["port"]

    client = TisUdpClient(hass, host, port)
    coordinator = TisCoordinator(hass, client)

    await coordinator.async_start()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # non-blocking first discovery
    hass.async_create_task(coordinator.async_discover())

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator: TisCoordinator = hass.data[DOMAIN].pop(entry.entry_id)

    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    await coordinator.async_stop()
    return ok

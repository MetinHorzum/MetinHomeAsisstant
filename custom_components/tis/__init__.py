from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN

PLATFORMS = ["sensor", "button"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    from .coordinator import TisUdpClient, TisCoordinator

    host = entry.data["host"]
    port = entry.data["port"]
    broadcast = entry.data.get("broadcast", "255.255.255.255")

    client = TisUdpClient(hass, host, port, broadcast)
    coordinator = TisCoordinator(hass, client)
    await coordinator.async_start()

    # Do one discovery right away so entities show something immediately
    await coordinator.async_discover(show_notification=True)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = hass.data[DOMAIN].pop(entry.entry_id)
    await coordinator.client.async_stop()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

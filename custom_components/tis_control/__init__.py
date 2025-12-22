"""The TIS Control integration."""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.LIGHT,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.COVER,
    Platform.CLIMATE,
    Platform.SELECT,
    Platform.LOCK,
    Platform.FAN,
    Platform.BUTTON,
]


@dataclass
class TISData:
    """Data for TIS integration."""
    api: object


type TISConfigEntry = ConfigEntry[TISData]


async def async_setup_entry(hass: HomeAssistant, entry: TISConfigEntry) -> bool:
    """Set up TIS Control from a config entry."""
    try:
        # Import TIS modules only when needed to avoid import errors
        from TISControlProtocol.api import TISApi
        
        port = entry.data[CONF_PORT]
        
        # Initialize TIS API
        tis_api = TISApi(
            port=port,
            hass=hass,
            domain=DOMAIN,
            devices_dict={},  # Will be populated by TIS library
            display_logo="./custom_components/tis_control/images/logo.png",
            version="1.0.9"
        )
        
        # Store API instance
        entry.runtime_data = TISData(api=tis_api)
        
        # Setup platforms
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        
        return True
        
    except ImportError:
        _LOGGER.error("TISControlProtocol library not found. Please install it first.")
        raise ConfigEntryNotReady("TISControlProtocol library not installed")
    except Exception as err:
        _LOGGER.error("Error setting up TIS Control: %s", err)
        raise ConfigEntryNotReady(f"Error connecting to TIS API: {err}")


async def async_unload_entry(hass: HomeAssistant, entry: TISConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        # Cleanup if needed
        pass
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: TISConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
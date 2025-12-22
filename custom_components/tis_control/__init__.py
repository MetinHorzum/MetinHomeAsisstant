"""The TIS Control integration."""
from __future__ import annotations

import logging
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
    mock_mode: bool = False


type TISConfigEntry = ConfigEntry[TISData]


class MockTISApi:
    """Mock TIS API for when library is not available."""
    
    def __init__(self, port: int, hass: HomeAssistant, **kwargs):
        self.port = port
        self.hass = hass
        self._connected = False
        _LOGGER.warning("Running in mock mode - TISControlProtocol library not found")
    
    async def connect(self):
        """Mock connect method."""
        self._connected = True
        return True
    
    async def get_entities(self, platform: str):
        """Mock get_entities method."""
        # Return empty list for now
        return []


async def async_setup_entry(hass: HomeAssistant, entry: TISConfigEntry) -> bool:
    """Set up TIS Control from a config entry."""
    port = entry.data[CONF_PORT]
    mock_mode = False
    
    try:
        # Try to import TIS modules
        from TISControlProtocol.api import TISApi
        
        # Initialize TIS API
        tis_api = TISApi(
            port=port,
            hass=hass,
            domain=DOMAIN,
            devices_dict={},  # Will be populated by TIS library
            display_logo="./custom_components/tis_control/images/logo.png",
            version="1.0.9"
        )
        
        _LOGGER.info("TISControlProtocol library loaded successfully")
        
    except ImportError:
        _LOGGER.warning(
            "TISControlProtocol library not found. Running in mock mode. "
            "Install it with: pip install TISControlProtocol==1.0.5 aiofiles ruamel.yaml psutil"
        )
        tis_api = MockTISApi(port=port, hass=hass)
        mock_mode = True
    
    try:
        # Test connection
        await tis_api.connect()
        
        # Store API instance
        entry.runtime_data = TISData(api=tis_api, mock_mode=mock_mode)
        
        # Setup platforms only if not in mock mode
        if not mock_mode:
            await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        else:
            _LOGGER.info("Skipping platform setup in mock mode")
        
        return True
        
    except Exception as err:
        if mock_mode:
            # In mock mode, still allow setup
            entry.runtime_data = TISData(api=tis_api, mock_mode=mock_mode)
            return True
        else:
            _LOGGER.error("Error connecting to TIS API: %s", err)
            raise ConfigEntryNotReady(f"Error connecting to TIS API: {err}")


async def async_unload_entry(hass: HomeAssistant, entry: TISConfigEntry) -> bool:
    """Unload a config entry."""
    if entry.runtime_data.mock_mode:
        # In mock mode, nothing to unload
        return True
    
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        # Cleanup if needed
        pass
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: TISConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
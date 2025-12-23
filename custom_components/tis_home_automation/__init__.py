"""
TIS Home Automation - Home Assistant Custom Component
Home automation integration for TIS protocol devices.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    DOMAIN,
    CONF_LOCAL_IP,
    CONF_COMMUNICATION_TYPE,
    CONF_SERIAL_PORT,
    CONF_BAUDRATE,
    COMMUNICATION_TYPE_UDP,
    COMMUNICATION_TYPE_RS485,
    DEFAULT_UPDATE_INTERVAL,
    STARTUP_MESSAGE
)
from .coordinator import TISDataUpdateCoordinator

# Import TIS protocol library
try:
    from tis_protocol import (
        TISCommunicationManager,
        create_communication_manager,
        get_local_ip,
        get_available_serial_ports,
        TISCommunicationError
    )
    HAS_TIS_PROTOCOL = True
except ImportError:
    HAS_TIS_PROTOCOL = False

_LOGGER = logging.getLogger(__name__)

# Supported platforms
PLATFORMS: list[Platform] = [
    Platform.SWITCH,
    Platform.LIGHT,
    Platform.CLIMATE, 
    Platform.SENSOR,
    Platform.BINARY_SENSOR
]

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the TIS Home Automation integration."""
    if not HAS_TIS_PROTOCOL:
        _LOGGER.error("TIS Protocol library not found. Please install the tis_protocol module.")
        return False
    
    _LOGGER.info(STARTUP_MESSAGE)
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up TIS Home Automation from a config entry."""
    if not HAS_TIS_PROTOCOL:
        _LOGGER.error("TIS Protocol library not found")
        return False

    # Get configuration data
    config_data = entry.data
    communication_type = config_data.get(CONF_COMMUNICATION_TYPE, COMMUNICATION_TYPE_UDP)
    
    _LOGGER.info(f"Setting up TIS integration with {communication_type} communication")
    
    try:
        # Create communication manager based on configuration
        if communication_type == COMMUNICATION_TYPE_UDP:
            local_ip = config_data.get(CONF_LOCAL_IP, get_local_ip())
            port = config_data.get(CONF_PORT, 6000)
            
            comm_config = {
                "udp_config": {
                    "local_ip": local_ip,
                    "port": port
                }
            }
        
        elif communication_type == COMMUNICATION_TYPE_RS485:
            serial_port = config_data.get(CONF_SERIAL_PORT)
            baudrate = config_data.get(CONF_BAUDRATE, 9600)
            
            if not serial_port:
                _LOGGER.error("Serial port not specified for RS485 communication")
                return False
            
            comm_config = {
                "serial_config": {
                    "port": serial_port,
                    "baudrate": baudrate
                }
            }
        
        else:
            _LOGGER.error(f"Unsupported communication type: {communication_type}")
            return False
        
        # Create communication manager
        communication_manager = await create_communication_manager(**comm_config)
        
        # Create data update coordinator
        coordinator = TISDataUpdateCoordinator(
            hass=hass,
            communication_manager=communication_manager,
            update_interval=timedelta(seconds=DEFAULT_UPDATE_INTERVAL)
        )
        
        # Connect and perform initial discovery
        _LOGGER.info("Connecting to TIS devices...")
        connect_results = await communication_manager.connect_all()
        
        if not any(connect_results.values()):
            _LOGGER.error("Failed to connect to any TIS transport")
            return False
        
        _LOGGER.info(f"Connected transports: {connect_results}")
        
        # Perform device discovery
        _LOGGER.info("Starting device discovery...")
        local_ip = config_data.get(CONF_LOCAL_IP, get_local_ip())
        discovered_devices = await communication_manager.discover_devices(
            source_ip=local_ip,
            timeout=30.0
        )
        
        _LOGGER.info(f"Discovered {len(discovered_devices)} TIS devices")
        
        # Store coordinator and communication manager
        hass.data[DOMAIN][entry.entry_id] = {
            "coordinator": coordinator,
            "communication_manager": communication_manager,
            "discovered_devices": discovered_devices
        }
        
        # Forward setup to platforms
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        
        # Set up services
        await _async_setup_services(hass, communication_manager)
        
        _LOGGER.info("TIS Home Automation integration setup completed successfully")
        return True
        
    except Exception as e:
        _LOGGER.error(f"Failed to setup TIS integration: {e}")
        return False

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        # Disconnect communication manager
        entry_data = hass.data[DOMAIN].pop(entry.entry_id)
        communication_manager = entry_data["communication_manager"]
        
        try:
            await communication_manager.disconnect_all()
            _LOGGER.info("TIS communication manager disconnected")
        except Exception as e:
            _LOGGER.error(f"Error disconnecting TIS communication manager: {e}")
    
    return unload_ok

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)

async def _async_setup_services(hass: HomeAssistant, communication_manager: TISCommunicationManager):
    """Set up TIS custom services."""
    
    async def handle_discover_devices(call):
        """Handle discover devices service call."""
        try:
            source_ip = call.data.get("source_ip", get_local_ip())
            timeout = call.data.get("timeout", 30.0)
            
            _LOGGER.info(f"Manual device discovery requested (IP: {source_ip}, timeout: {timeout}s)")
            
            discovered = await communication_manager.discover_devices(
                source_ip=source_ip,
                timeout=timeout
            )
            
            _LOGGER.info(f"Manual discovery completed: {len(discovered)} devices found")
            
            # Update all coordinators with new devices
            for entry_id, entry_data in hass.data[DOMAIN].items():
                if isinstance(entry_data, dict) and "coordinator" in entry_data:
                    entry_data["discovered_devices"].update(discovered)
                    await entry_data["coordinator"].async_request_refresh()
                    
        except Exception as e:
            _LOGGER.error(f"Device discovery service error: {e}")
    
    async def handle_send_raw_command(call):
        """Handle send raw command service call."""
        try:
            device_id = call.data.get("device_id", [0x01, 0xFE])
            op_code = call.data.get("op_code", [0x00, 0x0E])
            source_ip = call.data.get("source_ip", get_local_ip())
            additional_data = call.data.get("additional_data", [])
            
            if isinstance(device_id, str):
                # Convert hex string to byte list
                device_id = [int(device_id[i:i+2], 16) for i in range(0, len(device_id), 2)]
            
            if isinstance(op_code, str):
                # Convert hex string to byte list  
                op_code = [int(op_code[i:i+2], 16) for i in range(0, len(op_code), 2)]
            
            _LOGGER.info(f"Sending raw command - Device: {device_id}, OpCode: {op_code}")
            
            result = await communication_manager.send_to_device(
                device_id=device_id,
                op_code=op_code,
                source_ip=source_ip,
                additional_data=additional_data
            )
            
            if result:
                _LOGGER.info("Raw command sent successfully")
            else:
                _LOGGER.error("Failed to send raw command")
                
        except Exception as e:
            _LOGGER.error(f"Raw command service error: {e}")
    
    # Register services
    hass.services.async_register(
        DOMAIN,
        "discover_devices",
        handle_discover_devices,
        schema=cv.make_entity_service_schema({
            cv.Optional("source_ip"): cv.string,
            cv.Optional("timeout", default=30.0): cv.positive_float,
        })
    )
    
    hass.services.async_register(
        DOMAIN,
        "send_raw_command", 
        handle_send_raw_command,
        schema=cv.make_entity_service_schema({
            cv.Required("device_id"): cv.ensure_list,
            cv.Required("op_code"): cv.ensure_list,
            cv.Optional("source_ip"): cv.string,
            cv.Optional("additional_data", default=[]): cv.ensure_list,
        })
    )

# Configuration schema for YAML configuration (optional)
CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)
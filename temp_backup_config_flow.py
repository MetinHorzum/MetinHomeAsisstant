"""
Configuration flow for TIS Home Automation integration.
Handles integration setup through Home Assistant UI.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv

from .const import (
    DOMAIN,
    CONF_LOCAL_IP,
    CONF_COMMUNICATION_TYPE,
    CONF_SERIAL_PORT,
    CONF_BAUDRATE,
    CONF_DISCOVERY_TIMEOUT,
    COMMUNICATION_TYPE_UDP,
    COMMUNICATION_TYPE_RS485,
    DEFAULT_LOCAL_IP,
    DEFAULT_UDP_PORT,
    DEFAULT_SERIAL_BAUDRATE,
    DEFAULT_DISCOVERY_TIMEOUT,
    STEP_USER,
    STEP_COMMUNICATION,
    STEP_UDP_CONFIG,
    STEP_SERIAL_CONFIG,
    STEP_DISCOVERY,
    ERROR_MESSAGES
)

# Import TIS protocol library
try:
    from .tis_protocol import (
        create_communication_manager,
        get_local_ip,
        get_available_serial_ports,
        TISCommunicationError,
        TISConnectionError
    )
    HAS_TIS_PROTOCOL = True
except ImportError:
    HAS_TIS_PROTOCOL = False

# Import mock system
from .mock_devices import (
    is_mock_mode_enabled,
    MockCommunicationManager
)

_LOGGER = logging.getLogger(__name__)

class TISConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for TIS Home Automation."""
    
    VERSION = 1
    
    def __init__(self):
        """Initialize config flow."""
        self.data: Dict[str, Any] = {}
        self.discovered_devices: Dict[str, Any] = {}
        self.communication_manager = None
    
    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Handle the initial step."""
        errors: Dict[str, str] = {}
        
        if user_input is not None:
            # Check if mock mode should be used
            if not HAS_TIS_PROTOCOL or is_mock_mode_enabled():
                _LOGGER.warning("Using mock mode for config flow")
                
                # Create mock configuration entry directly
                mock_config = {
                    "setup_name": user_input.get("setup_name", "TIS Home Automation (Mock Mode)"),
                    CONF_COMMUNICATION_TYPE: COMMUNICATION_TYPE_UDP,
                    CONF_LOCAL_IP: "127.0.0.1",
                    CONF_PORT: 6000,
                    CONF_DISCOVERY_TIMEOUT: 10.0,
                    "mock_mode": True
                }
                
                return self.async_create_entry(
                    title="TIS Home Automation (Mock Mode)",
                    data=mock_config,
                    description="TIS protokol entegrasyonu - Mock test modu"
                )
            
            # Store basic info and continue with real config
            self.data.update(user_input)
            return await self.async_step_communication()
        
        # Show initial form
        mock_warning = " (Mock Mode Aktif)" if (not HAS_TIS_PROTOCOL or is_mock_mode_enabled()) else ""
        
        schema = vol.Schema({
            vol.Required("setup_name", default=f"TIS Home Automation{mock_warning}"): cv.string,
        })
        
        description_placeholders = {
            "integration_name": "TIS Home Automation",
            "mode_info": "Mock test modu kullanılacak - gerçek cihaz aranmayacak" if (not HAS_TIS_PROTOCOL or is_mock_mode_enabled()) else "Gerçek TIS cihazları aranacak"
        }
        
        return self.async_show_form(
            step_id=STEP_USER,
            data_schema=schema,
            errors=errors,
            description_placeholders=description_placeholders
        )
    
    async def async_step_communication(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle communication type selection."""
        errors: Dict[str, str] = {}
        
        if user_input is not None:
            communication_type = user_input[CONF_COMMUNICATION_TYPE]
            self.data[CONF_COMMUNICATION_TYPE] = communication_type
            
            if communication_type == COMMUNICATION_TYPE_UDP:
                return await self.async_step_udp_config()
            elif communication_type == COMMUNICATION_TYPE_RS485:
                return await self.async_step_serial_config()
        
        # Get available serial ports
        available_ports = get_available_serial_ports() if HAS_TIS_PROTOCOL else []
        
        # Build communication options
        communication_options = [COMMUNICATION_TYPE_UDP]
        if available_ports:
            communication_options.append(COMMUNICATION_TYPE_RS485)
        
        schema = vol.Schema({
            vol.Required(CONF_COMMUNICATION_TYPE, default=COMMUNICATION_TYPE_UDP): vol.In(communication_options)
        })
        
        description_placeholders = {
            "udp_description": "UDP ağ üzerinden haberleşme (Port 6000)",
            "rs485_description": f"RS485 seri port haberleşmesi ({len(available_ports)} port mevcut)",
        }
        
        return self.async_show_form(
            step_id=STEP_COMMUNICATION,
            data_schema=schema,
            errors=errors,
            description_placeholders=description_placeholders
        )
    
    async def async_step_udp_config(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle UDP configuration."""
        errors: Dict[str, str] = {}
        
        if user_input is not None:
            try:
                # Validate and store UDP configuration
                local_ip = user_input[CONF_LOCAL_IP]
                port = user_input[CONF_PORT]
                
                self.data.update({
                    CONF_LOCAL_IP: local_ip,
                    CONF_PORT: port,
                })
                
                # Test UDP connection
                test_result = await self._test_udp_connection(local_ip, port)
                if test_result["success"]:
                    return await self.async_step_discovery()
                else:
                    errors["base"] = test_result["error"]
                    
            except Exception as e:
                _LOGGER.error(f"UDP configuration error: {e}")
                errors["base"] = "connection_error"
        
        # Get current local IP as default
        default_ip = get_local_ip() if HAS_TIS_PROTOCOL else DEFAULT_LOCAL_IP
        
        schema = vol.Schema({
            vol.Required(CONF_LOCAL_IP, default=default_ip): cv.string,
            vol.Required(CONF_PORT, default=DEFAULT_UDP_PORT): cv.port,
        })
        
        return self.async_show_form(
            step_id=STEP_UDP_CONFIG,
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "current_ip": default_ip,
                "default_port": str(DEFAULT_UDP_PORT)
            }
        )
    
    async def async_step_serial_config(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle RS485 serial configuration."""
        errors: Dict[str, str] = {}
        
        if user_input is not None:
            try:
                # Validate and store serial configuration
                serial_port = user_input[CONF_SERIAL_PORT]
                baudrate = user_input[CONF_BAUDRATE]
                
                self.data.update({
                    CONF_SERIAL_PORT: serial_port,
                    CONF_BAUDRATE: baudrate,
                })
                
                # Test serial connection
                test_result = await self._test_serial_connection(serial_port, baudrate)
                if test_result["success"]:
                    return await self.async_step_discovery()
                else:
                    errors["base"] = test_result["error"]
                    
            except Exception as e:
                _LOGGER.error(f"Serial configuration error: {e}")
                errors["base"] = "connection_error"
        
        # Get available serial ports
        available_ports = get_available_serial_ports() if HAS_TIS_PROTOCOL else []
        
        if not available_ports:
            return self.async_abort(reason="no_serial_ports")
        
        schema = vol.Schema({
            vol.Required(CONF_SERIAL_PORT): vol.In(available_ports),
            vol.Required(CONF_BAUDRATE, default=DEFAULT_SERIAL_BAUDRATE): vol.In([9600, 19200, 38400, 57600, 115200]),
        })
        
        return self.async_show_form(
            step_id=STEP_SERIAL_CONFIG,
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "available_ports": ", ".join(available_ports),
                "default_baudrate": str(DEFAULT_SERIAL_BAUDRATE)
            }
        )
    
    async def async_step_discovery(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle device discovery."""
        errors: Dict[str, str] = {}
        
        if user_input is not None:
            discovery_timeout = user_input[CONF_DISCOVERY_TIMEOUT]
            
            # Perform device discovery
            progress_result = await self._perform_device_discovery(discovery_timeout)
            
            if progress_result["success"]:
                # Store discovery results
                self.discovered_devices = progress_result["devices"]
                self.data[CONF_DISCOVERY_TIMEOUT] = discovery_timeout
                
                # Create the config entry
                return self.async_create_entry(
                    title=f"TIS Home Automation ({len(self.discovered_devices)} cihaz)",
                    data=self.data,
                    description=f"TIS protokol entegrasyonu - {self.data[CONF_COMMUNICATION_TYPE].upper()} haberleşme"
                )
            else:
                errors["base"] = progress_result["error"]
        
        schema = vol.Schema({
            vol.Required(CONF_DISCOVERY_TIMEOUT, default=DEFAULT_DISCOVERY_TIMEOUT): vol.All(
                vol.Coerce(float), vol.Range(min=10.0, max=120.0)
            ),
        })
        
        description_placeholders = {
            "communication_type": self.data[CONF_COMMUNICATION_TYPE].upper(),
            "communication_details": self._get_communication_details()
        }
        
        return self.async_show_form(
            step_id=STEP_DISCOVERY,
            data_schema=schema,
            errors=errors,
            description_placeholders=description_placeholders
        )
    
    def _get_communication_details(self) -> str:
        """Get communication details string."""
        if self.data[CONF_COMMUNICATION_TYPE] == COMMUNICATION_TYPE_UDP:
            return f"{self.data[CONF_LOCAL_IP]}:{self.data[CONF_PORT]}"
        elif self.data[CONF_COMMUNICATION_TYPE] == COMMUNICATION_TYPE_RS485:
            return f"{self.data[CONF_SERIAL_PORT]} @ {self.data[CONF_BAUDRATE]} baud"
        return ""
    
    async def _test_udp_connection(self, local_ip: str, port: int) -> Dict[str, Any]:
        """Test UDP connection configuration."""
        try:
            # Create temporary communication manager
            comm_config = {
                "udp_config": {
                    "local_ip": local_ip,
                    "port": port
                }
            }
            
            test_manager = await create_communication_manager(**comm_config)
            
            # Try to connect
            connect_results = await test_manager.connect_all()
            
            # Cleanup
            await test_manager.disconnect_all()
            
            if any(connect_results.values()):
                return {"success": True}
            else:
                return {"success": False, "error": "udp_connection_failed"}
                
        except Exception as e:
            _LOGGER.error(f"UDP connection test failed: {e}")
            return {"success": False, "error": "connection_error"}
    
    async def _test_serial_connection(self, port: str, baudrate: int) -> Dict[str, Any]:
        """Test RS485 serial connection configuration."""
        try:
            # Create temporary communication manager
            comm_config = {
                "serial_config": {
                    "port": port,
                    "baudrate": baudrate
                }
            }
            
            test_manager = await create_communication_manager(**comm_config)
            
            # Try to connect
            connect_results = await test_manager.connect_all()
            
            # Cleanup
            await test_manager.disconnect_all()
            
            if any(connect_results.values()):
                return {"success": True}
            else:
                return {"success": False, "error": "serial_connection_failed"}
                
        except Exception as e:
            _LOGGER.error(f"Serial connection test failed: {e}")
            return {"success": False, "error": "connection_error"}
    
    async def _perform_device_discovery(self, timeout: float) -> Dict[str, Any]:
        """Perform TIS device discovery."""
        try:
            # Create communication manager based on configuration
            if self.data[CONF_COMMUNICATION_TYPE] == COMMUNICATION_TYPE_UDP:
                comm_config = {
                    "udp_config": {
                        "local_ip": self.data[CONF_LOCAL_IP],
                        "port": self.data[CONF_PORT]
                    }
                }
            elif self.data[CONF_COMMUNICATION_TYPE] == COMMUNICATION_TYPE_RS485:
                comm_config = {
                    "serial_config": {
                        "port": self.data[CONF_SERIAL_PORT],
                        "baudrate": self.data[CONF_BAUDRATE]
                    }
                }
            else:
                return {"success": False, "error": "invalid_communication_type"}
            
            # Create and connect communication manager
            self.communication_manager = await create_communication_manager(**comm_config)
            connect_results = await self.communication_manager.connect_all()
            
            if not any(connect_results.values()):
                return {"success": False, "error": "connection_failed"}
            
            # Perform device discovery
            _LOGGER.info(f"Starting TIS device discovery (timeout: {timeout}s)")
            
            local_ip = self.data.get(CONF_LOCAL_IP, get_local_ip())
            discovered = await self.communication_manager.discover_devices(
                source_ip=local_ip,
                timeout=timeout
            )
            
            # Cleanup
            await self.communication_manager.disconnect_all()
            
            _LOGGER.info(f"Discovery completed: found {len(discovered)} devices")
            
            return {
                "success": True,
                "devices": discovered,
                "count": len(discovered)
            }
            
        except TISConnectionError as e:
            _LOGGER.error(f"TIS connection error during discovery: {e}")
            return {"success": False, "error": "connection_failed"}
        except TISCommunicationError as e:
            _LOGGER.error(f"TIS communication error during discovery: {e}")
            return {"success": False, "error": "discovery_failed"}
        except Exception as e:
            _LOGGER.error(f"Unexpected error during discovery: {e}")
            return {"success": False, "error": "unknown_error"}
        finally:
            # Ensure cleanup
            if self.communication_manager:
                try:
                    await self.communication_manager.disconnect_all()
                except:
                    pass
    
    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get options flow for this integration."""
        return TISOptionsFlowHandler(config_entry)

class TISOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle TIS integration options."""
    
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
    
    async def async_step_init(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Manage integration options."""
        errors: Dict[str, str] = {}
        
        if user_input is not None:
            # Update options
            return self.async_create_entry(title="", data=user_input)
        
        # Current configuration
        current_config = self.config_entry.data
        communication_type = current_config.get(CONF_COMMUNICATION_TYPE, COMMUNICATION_TYPE_UDP)
        
        # Build options schema based on communication type
        if communication_type == COMMUNICATION_TYPE_UDP:
            schema = vol.Schema({
                vol.Optional(
                    CONF_LOCAL_IP, 
                    default=current_config.get(CONF_LOCAL_IP, get_local_ip())
                ): cv.string,
                vol.Optional(
                    CONF_PORT,
                    default=current_config.get(CONF_PORT, DEFAULT_UDP_PORT)
                ): cv.port,
                vol.Optional(
                    CONF_DISCOVERY_TIMEOUT,
                    default=current_config.get(CONF_DISCOVERY_TIMEOUT, DEFAULT_DISCOVERY_TIMEOUT)
                ): vol.All(vol.Coerce(float), vol.Range(min=10.0, max=120.0)),
            })
        else:  # RS485
            available_ports = get_available_serial_ports() if HAS_TIS_PROTOCOL else []
            
            schema = vol.Schema({
                vol.Optional(
                    CONF_SERIAL_PORT,
                    default=current_config.get(CONF_SERIAL_PORT)
                ): vol.In(available_ports) if available_ports else cv.string,
                vol.Optional(
                    CONF_BAUDRATE,
                    default=current_config.get(CONF_BAUDRATE, DEFAULT_SERIAL_BAUDRATE)
                ): vol.In([9600, 19200, 38400, 57600, 115200]),
                vol.Optional(
                    CONF_DISCOVERY_TIMEOUT,
                    default=current_config.get(CONF_DISCOVERY_TIMEOUT, DEFAULT_DISCOVERY_TIMEOUT)
                ): vol.All(vol.Coerce(float), vol.Range(min=10.0, max=120.0)),
            })
        
        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "communication_type": communication_type.upper(),
                "current_config": str(current_config)
            }
        )
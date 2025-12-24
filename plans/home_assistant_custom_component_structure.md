# Home Assistant TIS Automation Custom Component

## 📂 Component Klasör Yapısı

```
custom_components/tis_automation/
├── __init__.py                 # Ana component entry point
├── manifest.json               # Component metadata
├── config_flow.py             # Kurulum sihirbazı
├── const.py                   # Sabitler ve konfigürasyon
├── coordinator.py             # Data update coordinator
├── device.py                  # TIS device wrapper
├── entity.py                  # Base TIS entity class
├── switch.py                  # Switch entity implementation
├── light.py                   # Light entity implementation
├── climate.py                 # Climate entity implementation
├── sensor.py                  # Sensor entity implementation
├── binary_sensor.py           # Binary sensor implementation
├── cover.py                   # Cover entity (perdeler/jaluziler)
├── scene.py                   # Scene entity (opsiyonel)
├── services.yaml              # Custom services tanımları
├── strings.json               # UI strings (İngilizce)
└── translations/
    ├── en.json                # İngilizce çeviriler
    └── tr.json                # Türkçe çeviriler
```

## 📄 manifest.json

```json
{
  "domain": "tis_automation",
  "name": "TIS Home Automation",
  "version": "1.0.0",
  "documentation": "https://github.com/your-username/tis-homeassistant",
  "issue_tracker": "https://github.com/your-username/tis-homeassistant/issues",
  "dependencies": [
    "zeroconf"
  ],
  "requirements": [
    "pyserial-asyncio>=0.6",
    "construct>=2.10"
  ],
  "codeowners": [
    "@your-username"
  ],
  "config_flow": true,
  "iot_class": "local_push",
  "integration_type": "hub",
  "loggers": [
    "custom_components.tis_automation"
  ]
}
```

## 🏠 __init__.py (Ana Component)

### Platform Setup ve Device Coordination

```python
"""TIS Home Automation integration for Home Assistant."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    DOMAIN,
    PLATFORMS,
    DEFAULT_SCAN_INTERVAL,
    CONF_UDP_PORT,
    CONF_RS485_PORT,
    CONF_RS485_ENABLED,
    CONF_UDP_ENABLED,
)
from .coordinator import TISDataUpdateCoordinator
from .tis_protocol import TISCommunicationManager

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SWITCH,
    Platform.LIGHT, 
    Platform.CLIMATE,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.COVER,
]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up TIS Automation from a config entry."""
    
    # Communication manager setup
    config = {
        "udp_enabled": entry.data.get(CONF_UDP_ENABLED, True),
        "udp_port": entry.data.get(CONF_UDP_PORT, 6000),
        "udp_interface": entry.data.get("udp_interface", "0.0.0.0"),
        "rs485_enabled": entry.data.get(CONF_RS485_ENABLED, False),
        "rs485_port": entry.data.get(CONF_RS485_PORT),
        "rs485_baudrate": entry.data.get("rs485_baudrate", 9600),
    }
    
    # Initialize TIS communication
    comm_manager = TISCommunicationManager(config)
    
    if not await comm_manager.initialize():
        _LOGGER.error("Failed to initialize TIS communication")
        return False
    
    # Device discovery
    try:
        devices = await comm_manager.discover_devices(timeout=30)
        _LOGGER.info("Discovered %d TIS devices", len(devices))
        
        if not devices:
            _LOGGER.warning("No TIS devices found on network")
            
    except Exception as e:
        _LOGGER.error("Device discovery failed: %s", e)
        return False
    
    # Data update coordinator
    scan_interval = timedelta(seconds=entry.options.get("scan_interval", DEFAULT_SCAN_INTERVAL))
    
    coordinator = TISDataUpdateCoordinator(
        hass=hass,
        logger=_LOGGER,
        name=DOMAIN,
        update_interval=scan_interval,
        communication_manager=comm_manager,
        devices=devices,
    )
    
    # Initial data fetch
    await coordinator.async_config_entry_first_refresh()
    
    # Store coordinator in hass.data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "comm_manager": comm_manager,
        "devices": devices,
    }
    
    # Setup platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Start monitoring
    await comm_manager.start_monitoring()
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    
    # Stop monitoring
    data = hass.data[DOMAIN][entry.entry_id]
    comm_manager = data["comm_manager"]
    await comm_manager.stop_monitoring()
    await comm_manager.disconnect()
    
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        
    return unload_ok

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
```

## ⚙️ config_flow.py (Kurulum Sihirbazı)

### Kullanıcı Dostu Kurulum Akışı

```python
"""Config flow for TIS Automation integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    DEFAULT_NAME,
    DEFAULT_UDP_PORT,
    DEFAULT_RS485_BAUDRATE,
    CONF_UDP_ENABLED,
    CONF_UDP_PORT,
    CONF_RS485_ENABLED,
    CONF_RS485_PORT,
    CONF_RS485_BAUDRATE,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
)
from .tis_protocol import TISCommunicationManager

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA_UDP = vol.Schema({
    vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
    vol.Optional(CONF_UDP_PORT, default=DEFAULT_UDP_PORT): cv.port,
    vol.Optional("udp_interface", default="0.0.0.0"): str,
})

DATA_SCHEMA_RS485 = vol.Schema({
    vol.Required(CONF_RS485_PORT): str,
    vol.Optional(CONF_RS485_BAUDRATE, default=DEFAULT_RS485_BAUDRATE): vol.In([9600, 19200, 38400, 57600, 115200]),
    vol.Optional("rs485_parity", default="EVEN"): vol.In(["NONE", "EVEN", "ODD"]),
})

class TISConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for TIS Automation."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    def __init__(self):
        """Initialize the config flow."""
        self.data = {}
        self.discovered_devices = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - connection type selection."""
        
        if user_input is not None:
            self.data.update(user_input)
            
            if user_input.get("connection_type") == "udp":
                return await self.async_step_udp()
            elif user_input.get("connection_type") == "rs485":
                return await self.async_step_rs485()
            elif user_input.get("connection_type") == "both":
                return await self.async_step_udp()
        
        schema = vol.Schema({
            vol.Required("connection_type", default="udp"): vol.In({
                "udp": "UDP Network (Önerilen)",
                "rs485": "RS485 Serial",
                "both": "Her ikisi de"
            }),
        })
        
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            description_placeholders={
                "name": DEFAULT_NAME,
            }
        )

    async def async_step_udp(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle UDP configuration."""
        errors = {}
        
        if user_input is not None:
            self.data.update(user_input)
            self.data[CONF_UDP_ENABLED] = True
            
            # Test UDP connection
            try:
                await self._test_udp_connection(user_input)
                
                # Check if we also need RS485
                if self.data.get("connection_type") == "both":
                    self.data[CONF_RS485_ENABLED] = True
                    return await self.async_step_rs485()
                else:
                    self.data[CONF_RS485_ENABLED] = False
                    return await self.async_step_discovery()
                    
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="udp",
            data_schema=DATA_SCHEMA_UDP,
            errors=errors,
        )

    async def async_step_rs485(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle RS485 configuration."""
        errors = {}
        
        if user_input is not None:
            self.data.update(user_input)
            
            # Test RS485 connection
            try:
                await self._test_rs485_connection(user_input)
                return await self.async_step_discovery()
                
            except CannotConnect:
                errors["base"] = "cannot_connect_rs485"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="rs485",
            data_schema=DATA_SCHEMA_RS485,
            errors=errors,
        )

    async def async_step_discovery(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle device discovery."""
        if user_input is not None:
            # Discovery tamamlandı, entry oluştur
            return self.async_create_entry(
                title=self.data.get(CONF_NAME, DEFAULT_NAME),
                data=self.data,
            )
        
        # Device discovery yap
        try:
            comm_manager = TISCommunicationManager(self.data)
            await comm_manager.initialize()
            
            self.discovered_devices = await comm_manager.discover_devices(timeout=15)
            
            await comm_manager.disconnect()
            
        except Exception as e:
            _LOGGER.error("Discovery failed: %s", e)
            return self.async_show_form(
                step_id="discovery",
                errors={"base": "discovery_failed"},
            )
        
        return self.async_show_form(
            step_id="discovery",
            description_placeholders={
                "device_count": len(self.discovered_devices),
                "devices": "\n".join([
                    f"• {device.model_name} ({device.device_id})" 
                    for device in self.discovered_devices[:10]
                ]),
            },
        )

    async def _test_udp_connection(self, config: dict) -> None:
        """Test UDP connection."""
        test_config = {
            "udp_enabled": True,
            "udp_port": config.get(CONF_UDP_PORT, DEFAULT_UDP_PORT),
            "udp_interface": config.get("udp_interface", "0.0.0.0"),
            "rs485_enabled": False,
        }
        
        comm_manager = TISCommunicationManager(test_config)
        
        try:
            if not await comm_manager.initialize():
                raise CannotConnect("UDP initialization failed")
                
            # Quick discovery test
            devices = await comm_manager.discover_devices(timeout=5)
            _LOGGER.info("UDP test: found %d devices", len(devices))
            
        finally:
            await comm_manager.disconnect()

    async def _test_rs485_connection(self, config: dict) -> None:
        """Test RS485 connection."""
        test_config = {
            "udp_enabled": False,
            "rs485_enabled": True,
            "rs485_port": config.get(CONF_RS485_PORT),
            "rs485_baudrate": config.get(CONF_RS485_BAUDRATE, DEFAULT_RS485_BAUDRATE),
        }
        
        comm_manager = TISCommunicationManager(test_config)
        
        try:
            if not await comm_manager.initialize():
                raise CannotConnect("RS485 initialization failed")
                
        finally:
            await comm_manager.disconnect()

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get options flow."""
        return TISOptionsFlowHandler(config_entry)

class TISOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for TIS Automation."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options_schema = vol.Schema({
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=self.config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ): cv.positive_int,
            vol.Optional(
                "enable_debug_logging",
                default=self.config_entry.options.get("enable_debug_logging", False),
            ): bool,
        })

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
        )

class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""
```

## 🎛️ const.py (Sabitler)

### Configuration ve Platform Constants

```python
"""Constants for the TIS Automation integration."""
from homeassistant.const import Platform

DOMAIN = "tis_automation"
DEFAULT_NAME = "TIS Home Automation"

# Configuration constants
CONF_UDP_ENABLED = "udp_enabled"
CONF_UDP_PORT = "udp_port"
CONF_RS485_ENABLED = "rs485_enabled"
CONF_RS485_PORT = "rs485_port"
CONF_RS485_BAUDRATE = "rs485_baudrate"
CONF_SCAN_INTERVAL = "scan_interval"

# Default values
DEFAULT_UDP_PORT = 6000
DEFAULT_RS485_BAUDRATE = 9600
DEFAULT_SCAN_INTERVAL = 30  # seconds

# Platforms
PLATFORMS = [
    Platform.SWITCH,
    Platform.LIGHT,
    Platform.CLIMATE,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.COVER,
]

# TIS Device Types (Analiz sonuçlarından)
TIS_DEVICE_TYPES = {
    # Lighting
    0x0001: "Single Channel Lighting",
    0x0258: "Dimmer 6CH 2A", 
    0x0259: "Dimmer 4CH 3A",
    
    # Climate Control
    0x806C: "TIS-MER-AC4G-PB",
    0x0077: "HVAC6-3A-T",
    
    # Sensors
    0x8022: "TIS-HEALTH-CM",
    0x0076: "TIS-4DI-IN",
    
    # Switches
    0x0051: "Universal Switch Type 1",
    0x0052: "Universal Switch Type 2",
    0x0056: "Scene Switch",
    
    # Security
    0x0030: "Security Module",
    0x0BE9: "TIS-SEC-SM",
}

# TIS OpCodes (Protokol analizinden)
TIS_OPCODES = {
    # Discovery
    "DISCOVERY_REQUEST": 0x000E,
    "DISCOVERY_RESPONSE": 0x000F,
    
    # Device Control
    "DEVICE_CONTROL": 0x0031,
    "DEVICE_STATUS": 0x0032,
    "DEVICE_UPDATE": 0x0033,
    "DEVICE_UPDATE_RESPONSE": 0x0034,
    
    # AC Control
    "AC_CONTROL": 0xE0EE,
    "AC_STATUS": 0xE0ED,
    "AC_QUERY": 0xA12E,
    "AC_RESPONSE": 0xA12F,
    
    # Sensors
    "SENSOR_QUERY": 0x2024,
    "SENSOR_RESPONSE": 0x2025,
    
    # System
    "FIRMWARE_QUERY": 0xEFFD,
    "FIRMWARE_RESPONSE": 0xEFFE,
    "STATUS_QUERY": 0x0280,
    "STATUS_RESPONSE": 0x0281,
}

# Entity mapping (Device Type -> HA Entities)
DEVICE_ENTITY_MAP = {
    0x0001: ["light"],  # Single Channel Lighting
    0x0258: ["light"],  # Dimmer 6CH
    0x0259: ["light"],  # Dimmer 4CH
    0x806C: ["climate", "sensor"],  # AC Panel
    0x8022: ["sensor"],  # Health Sensor
    0x0076: ["binary_sensor"],  # Digital Input
    0x0051: ["switch"],  # Universal Switch
    0x0056: ["switch"],  # Scene Switch
}

# Service names
SERVICE_SEND_COMMAND = "send_command"
SERVICE_DISCOVER_DEVICES = "discover_devices"
SERVICE_EXECUTE_SCENE = "execute_scene"

# Attributes
ATTR_DEVICE_TYPE = "device_type"
ATTR_FIRMWARE_VERSION = "firmware_version"
ATTR_LAST_SEEN = "last_seen"
ATTR_TRANSPORT = "transport"
ATTR_TIS_DEVICE_ID = "tis_device_id"
```

## 📊 coordinator.py (Data Update Coordinator)

### Centralized Data Management

```python
"""TIS Automation data update coordinator."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, TIS_OPCODES
from .tis_protocol import TISCommunicationManager, TISDevice

_LOGGER = logging.getLogger(__name__)

class TISDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from TIS devices."""

    def __init__(
        self,
        hass: HomeAssistant,
        logger: logging.Logger,
        *,
        name: str,
        update_interval: timedelta,
        communication_manager: TISCommunicationManager,
        devices: list[TISDevice],
    ) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass,
            logger,
            name=name,
            update_interval=update_interval,
        )
        
        self.comm_manager = communication_manager
        self.devices = {device.device_id: device for device in devices}
        self.device_data = {}
        
    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via TIS communication manager."""
        try:
            updated_data = {}
            
            # Her cihaz için durum sorgula
            for device_id, device in self.devices.items():
                try:
                    # Device-specific status query
                    device_data = await self._query_device_status(device)
                    updated_data[device_id] = device_data
                    
                    # Update device last_seen
                    device.update_last_seen()
                    
                except Exception as e:
                    _LOGGER.warning("Failed to update device %s: %s", device_id, e)
                    # Keep previous data if available
                    if device_id in self.device_data:
                        updated_data[device_id] = self.device_data[device_id]
                    
            self.device_data = updated_data
            return updated_data
            
        except Exception as e:
            raise UpdateFailed(f"Error communicating with TIS system: {e}") from e
    
    async def _query_device_status(self, device: TISDevice) -> dict[str, Any]:
        """Query status for a specific device."""
        device_data = {
            "device_id": device.device_id,
            "online": False,
            "last_seen": device.last_seen,
        }
        
        try:
            # Climate devices (AC control)
            if 0x806C in [device.device_type]:  # TIS-MER-AC4G-PB
                ac_data = await self._query_ac_status(device)
                device_data.update(ac_data)
                
            # Sensor devices
            elif device.device_type == 0x8022:  # Health Sensor
                sensor_data = await self._query_health_sensor(device)
                device_data.update(sensor_data)
                
            # Lighting devices
            elif device.device_type in [0x0001, 0x0258, 0x0259]:
                light_data = await self._query_light_status(device)
                device_data.update(light_data)
                
            # Switch devices  
            elif device.device_type in [0x0051, 0x0052, 0x0056]:
                switch_data = await self._query_switch_status(device)
                device_data.update(switch_data)
                
            # Binary sensor devices
            elif device.device_type == 0x0076:  # Digital Input
                binary_data = await self._query_binary_sensor(device)
                device_data.update(binary_data)
                
            # Generic status query
            else:
                generic_data = await self._query_generic_status(device)
                device_data.update(generic_data)
                
            device_data["online"] = True
            
        except Exception as e:
            _LOGGER.debug("Device %s query failed: %s", device.device_id, e)
            
        return device_data
    
    async def _query_ac_status(self, device: TISDevice) -> dict[str, Any]:
        """Query AC device status."""
        ac_data = {}
        
        # AC control query
        response = await self.comm_manager.send_command(
            device.device_id,
            TIS_OPCODES["AC_QUERY"],  # 0xA12E
            timeout=3.0
        )
        
        if response.success and len(response.data) >= 8:
            # Parse AC status (Implementation'dan alınan format)
            data = response.data
            ac_data.update({
                "hvac_mode": "cool" if data[1] == 0x00 else "heat" if data[1] == 0x01 else "off",
                "current_temperature": data[3] if data[3] != 0xFF else None,
                "target_temperature": data[2],
                "fan_mode": ["auto", "low", "medium", "high"][min(data[4], 3)],
                "power_state": data[0] == 0x01,
            })
            
        return ac_data
    
    async def _query_health_sensor(self, device: TISDevice) -> dict[str, Any]:
        """Query health sensor data."""
        sensor_data = {}
        
        response = await self.comm_manager.send_command(
            device.device_id,
            TIS_OPCODES["SENSOR_QUERY"],  # 0x2024
            timeout=3.0
        )
        
        if response.success and len(response.data) >= 15:
            data = response.data
            # Health sensor format (Analiz sonuçlarından)
            sensor_data.update({
                "temperature": data[13],  # °C
                "humidity": data[14],  # %
                "co2": (data[9] << 8) | data[10],  # ppm
                "tvoc": (data[11] << 8) | data[12],  # ppb
                "lux": (data[5] << 8) | data[6],  # lux
                "noise": (data[7] << 8) | data[8],  # dB
            })
            
        return sensor_data
    
    async def _query_light_status(self, device: TISDevice) -> dict[str, Any]:
        """Query light device status."""
        light_data = {}
        
        response = await self.comm_manager.send_command(
            device.device_id,
            TIS_OPCODES["DEVICE_STATUS"],  # 0x0032
            timeout=2.0
        )
        
        if response.success and len(response.data) >= 3:
            data = response.data
            light_data.update({
                "brightness": data[2],  # 0-100
                "is_on": data[2] > 0,
                "channel": data[0],
            })
            
        return light_data
    
    async def _query_switch_status(self, device: TISDevice) -> dict[str, Any]:
        """Query switch device status."""
        switch_data = {}
        
        response = await self.comm_manager.send_command(
            device.device_id,
            TIS_OPCODES["DEVICE_STATUS"],  # 0x0032
            timeout=2.0
        )
        
        if response.success and len(response.data) >= 2:
            data = response.data
            switch_data.update({
                "is_on": data[1] == 0x01,
                "channel": data[0],
            })
            
        return switch_data
    
    async def _query_binary_sensor(self, device: TISDevice) -> dict[str, Any]:
        """Query binary sensor status."""
        binary_data = {}
        
        response = await self.comm_manager.send_command(
            device.device_id,
            0x012C,  # Digital Input query
            timeout=2.0
        )
        
        if response.success:
            data = response.data
            # 4 channel binary sensor
            binary_data.update({
                "channels": {
                    0: data[2] if len(data) > 2 else 0,
                    1: data[3] if len(data) > 3 else 0,
                    2: data[4] if len(data) > 4 else 0,
                    3: data[5] if len(data) > 5 else 0,
                }
            })
            
        return binary_data
    
    async def _query_generic_status(self, device: TISDevice) -> dict[str, Any]:
        """Generic device status query."""
        generic_data = {}
        
        response = await self.comm_manager.send_command(
            device.device_id,
            TIS_OPCODES["STATUS_QUERY"],  # 0x0280
            timeout=2.0
        )
        
        if response.success:
            generic_data["status"] = "online"
            
        return generic_data
    
    async def send_device_command(self, device_id: str, op_code: int, data: bytes = b'') -> bool:
        """Send command to device."""
        try:
            response = await self.comm_manager.send_command(device_id, op_code, data)
            return response.success
        except Exception as e:
            _LOGGER.error("Failed to send command to device %s: %s", device_id, e)
            return False
    
    def get_device(self, device_id: str) -> TISDevice | None:
        """Get device by ID."""
        return self.devices.get(device_id)
        
    def get_device_data(self, device_id: str) -> dict[str, Any] | None:
        """Get device data."""
        return self.device_data.get(device_id)
```

Bu yapı, Home Assistant'ın modern integration patterns'ini takip ederek:

- ✅ **Config Flow**: Kullanıcı dostu kurulum sihirbazı
- ✅ **Data Coordinator**: Efficient veri güncelleme  
- ✅ **Multi-transport**: Hem UDP hem RS485 desteği
- ✅ **Device Discovery**: Otomatik cihaz keşfi
- ✅ **Error Handling**: Robust hata yönetimi
- ✅ **Translation Support**: Çoklu dil desteği

Sıradaki adım entity implementation'ları olacak.
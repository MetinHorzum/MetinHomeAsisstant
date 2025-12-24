# TIS Base Entity ve Services Planı

## 🏗️ Base Entity Class (entity.py)

### Common Entity Functionality

```python
"""Base entity for TIS Automation."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, ATTR_TIS_DEVICE_ID, ATTR_DEVICE_TYPE, ATTR_FIRMWARE_VERSION
from .coordinator import TISDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

class TISBaseEntity(CoordinatorEntity):
    """Base entity for TIS devices."""

    def __init__(
        self,
        coordinator: TISDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize TIS base entity."""
        super().__init__(coordinator)
        
        self.device_id = device_id
        self.device = coordinator.get_device(device_id)
        
        if not self.device:
            raise ValueError(f"Device {device_id} not found in coordinator")

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for device registry."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.device_id)},
            name=self.device.model_name or f"TIS Device {self.device_id}",
            manufacturer="TIS Automation",
            model=self.device.get_model_description(),
            sw_version=self.device.firmware_version,
            via_device=(DOMAIN, self.device_id),  # Hub device
        )

    @property
    def should_poll(self) -> bool:
        """Return True if entity has to be polled for state."""
        return False

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        device_data = self.coordinator.get_device_data(self.device_id)
        return device_data is not None and device_data.get("online", False)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity specific state attributes."""
        attrs = {
            ATTR_TIS_DEVICE_ID: self.device_id,
            ATTR_DEVICE_TYPE: f"0x{self.device.device_type:04X}",
        }
        
        if self.device.firmware_version:
            attrs[ATTR_FIRMWARE_VERSION] = self.device.firmware_version
            
        device_data = self.coordinator.get_device_data(self.device_id)
        if device_data:
            if "last_seen" in device_data:
                attrs["last_seen"] = device_data["last_seen"]
            if "transport" in device_data:
                attrs["transport"] = device_data["transport"]
                
        return attrs

class TISDevice:
    """Wrapper for TIS device information."""
    
    def __init__(
        self,
        device_id: str,
        device_type: int,
        model_name: str = None,
        firmware_version: str = None,
        ip_address: str = None,
        serial_port: str = None,
        capabilities: dict = None,
    ) -> None:
        """Initialize TIS device."""
        self.device_id = device_id
        self.device_type = device_type
        self.model_name = model_name or f"TIS Device {device_type:04X}"
        self.firmware_version = firmware_version
        self.ip_address = ip_address
        self.serial_port = serial_port
        self.capabilities = capabilities or {}
        self.last_seen = None
        
    def get_model_description(self) -> str:
        """Get human readable model description."""
        from .const import TIS_DEVICE_TYPES
        return TIS_DEVICE_TYPES.get(self.device_type, f"Unknown TIS Device (0x{self.device_type:04X})")
    
    def update_last_seen(self) -> None:
        """Update last seen timestamp."""
        from datetime import datetime
        self.last_seen = datetime.now()
        
    def get_supported_entities(self) -> list[str]:
        """Get list of supported Home Assistant entity types."""
        from .const import DEVICE_ENTITY_MAP
        return DEVICE_ENTITY_MAP.get(self.device_type, [])
        
    def to_dict(self) -> dict[str, Any]:
        """Convert device to dictionary."""
        return {
            "device_id": self.device_id,
            "device_type": self.device_type,
            "model_name": self.model_name,
            "firmware_version": self.firmware_version,
            "ip_address": self.ip_address,
            "serial_port": self.serial_port,
            "capabilities": self.capabilities,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
        }
```

## 🛠️ Services Configuration (services.yaml)

### Custom TIS Services

```yaml
# TIS Automation Custom Services

send_command:
  name: Send TIS Command
  description: Send raw command to TIS device
  target:
    entity:
      domain: tis_automation
  fields:
    device_id:
      name: Device ID
      description: TIS device identifier
      required: true
      selector:
        text:
    opcode:
      name: Operation Code
      description: TIS protocol operation code (hex format like 0x0031)
      required: true
      selector:
        text:
    data:
      name: Command Data
      description: Command payload as hex string (optional)
      required: false
      selector:
        text:

discover_devices:
  name: Discover TIS Devices
  description: Scan for new TIS devices on the network
  fields:
    timeout:
      name: Timeout
      description: Discovery timeout in seconds
      required: false
      default: 30
      selector:
        number:
          min: 5
          max: 120
          step: 5

execute_scene:
  name: Execute TIS Scene
  description: Execute a TIS scene/scenario
  target:
    entity:
      domain: tis_automation
      integration: tis_automation
  fields:
    scene_id:
      name: Scene ID
      description: Scene identifier (1-255)
      required: true
      selector:
        number:
          min: 1
          max: 255
          step: 1

refresh_device:
  name: Refresh Device
  description: Force refresh device state
  target:
    entity:
      domain: tis_automation
      integration: tis_automation

reboot_device:
  name: Reboot Device  
  description: Reboot TIS device (if supported)
  target:
    entity:
      domain: tis_automation
      integration: tis_automation

set_device_parameter:
  name: Set Device Parameter
  description: Set device-specific parameter
  target:
    entity:
      domain: tis_automation
      integration: tis_automation
  fields:
    parameter_id:
      name: Parameter ID
      description: Parameter identifier
      required: true
      selector:
        number:
          min: 0
          max: 255
          step: 1
    value:
      name: Value
      description: Parameter value
      required: true
      selector:
        text:
```

## 🎯 Service Implementation (__init__.py eklentisi)

### Service Handler Functions

```python
# __init__.py içinde ek service handling kodu

import voluptuous as vol
from homeassistant.helpers import config_validation as cv

# Service schemas
SERVICE_SEND_COMMAND_SCHEMA = vol.Schema({
    vol.Required("device_id"): cv.string,
    vol.Required("opcode"): cv.string,
    vol.Optional("data", default=""): cv.string,
})

SERVICE_DISCOVER_DEVICES_SCHEMA = vol.Schema({
    vol.Optional("timeout", default=30): cv.positive_int,
})

SERVICE_EXECUTE_SCENE_SCHEMA = vol.Schema({
    vol.Required("scene_id"): cv.positive_int,
})

SERVICE_SET_PARAMETER_SCHEMA = vol.Schema({
    vol.Required("parameter_id"): cv.positive_int,
    vol.Required("value"): cv.string,
})

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up TIS Automation from a config entry."""
    
    # ... existing setup code ...
    
    # Register services
    async def async_send_command(call):
        """Handle send_command service call."""
        device_id = call.data["device_id"]
        opcode_str = call.data["opcode"]
        data_str = call.data.get("data", "")
        
        # Parse opcode
        try:
            if opcode_str.startswith("0x"):
                opcode = int(opcode_str, 16)
            else:
                opcode = int(opcode_str)
        except ValueError:
            _LOGGER.error("Invalid opcode format: %s", opcode_str)
            return
            
        # Parse data
        data = b''
        if data_str:
            try:
                # Convert hex string to bytes
                data = bytes.fromhex(data_str.replace("0x", "").replace(" ", ""))
            except ValueError:
                _LOGGER.error("Invalid data format: %s", data_str)
                return
        
        # Send command
        success = await coordinator.send_device_command(device_id, opcode, data)
        if success:
            _LOGGER.info("Command sent successfully to device %s", device_id)
        else:
            _LOGGER.error("Failed to send command to device %s", device_id)

    async def async_discover_devices(call):
        """Handle discover_devices service call."""
        timeout = call.data.get("timeout", 30)
        
        try:
            new_devices = await comm_manager.discover_devices(timeout=timeout)
            _LOGGER.info("Discovery found %d devices", len(new_devices))
            
            # Update coordinator with new devices
            for device in new_devices:
                if device.device_id not in coordinator.devices:
                    coordinator.devices[device.device_id] = device
                    _LOGGER.info("Added new device: %s", device.device_id)
                    
            await coordinator.async_request_refresh()
            
        except Exception as e:
            _LOGGER.error("Device discovery failed: %s", e)

    async def async_execute_scene(call):
        """Handle execute_scene service call."""
        scene_id = call.data["scene_id"]
        
        # Find scene switch devices
        scene_devices = [
            device_id for device_id, device in coordinator.devices.items()
            if device.device_type == 0x0056  # Scene Switch
        ]
        
        if not scene_devices:
            _LOGGER.warning("No scene switch devices found")
            return
            
        # Execute scene on first available scene device
        device_id = scene_devices[0]
        success = await coordinator.send_device_command(
            device_id,
            TIS_OPCODES["DEVICE_CONTROL"],  # 0x0031
            bytes([scene_id, 0x01])
        )
        
        if success:
            _LOGGER.info("Scene %d executed", scene_id)
        else:
            _LOGGER.error("Failed to execute scene %d", scene_id)

    async def async_refresh_device(call):
        """Handle refresh_device service call."""
        # Force coordinator refresh
        await coordinator.async_request_refresh()

    async def async_set_parameter(call):
        """Handle set_device_parameter service call."""
        parameter_id = call.data["parameter_id"]
        value_str = call.data["value"]
        
        try:
            value = int(value_str)
        except ValueError:
            _LOGGER.error("Invalid parameter value: %s", value_str)
            return
            
        # This would need device-specific implementation
        _LOGGER.info("Set parameter %d to %d", parameter_id, value)

    # Register services
    hass.services.async_register(
        DOMAIN,
        "send_command",
        async_send_command,
        schema=SERVICE_SEND_COMMAND_SCHEMA,
    )
    
    hass.services.async_register(
        DOMAIN,
        "discover_devices", 
        async_discover_devices,
        schema=SERVICE_DISCOVER_DEVICES_SCHEMA,
    )
    
    hass.services.async_register(
        DOMAIN,
        "execute_scene",
        async_execute_scene,
        schema=SERVICE_EXECUTE_SCENE_SCHEMA,
    )
    
    hass.services.async_register(
        DOMAIN,
        "refresh_device",
        async_refresh_device,
    )
    
    hass.services.async_register(
        DOMAIN,
        "set_device_parameter",
        async_set_parameter,
        schema=SERVICE_SET_PARAMETER_SCHEMA,
    )
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    
    # ... existing unload code ...
    
    # Remove services
    hass.services.async_remove(DOMAIN, "send_command")
    hass.services.async_remove(DOMAIN, "discover_devices")
    hass.services.async_remove(DOMAIN, "execute_scene") 
    hass.services.async_remove(DOMAIN, "refresh_device")
    hass.services.async_remove(DOMAIN, "set_device_parameter")
    
    return unload_ok
```

## 🌐 Translation Files

### strings.json (Ana Strings)

```json
{
  "config": {
    "flow_title": "TIS Home Automation",
    "step": {
      "user": {
        "title": "Connection Type",
        "description": "Choose how to connect to your TIS system",
        "data": {
          "connection_type": "Connection Type"
        }
      },
      "udp": {
        "title": "UDP Network Configuration",
        "description": "Configure UDP network connection for TIS devices",
        "data": {
          "name": "Name",
          "udp_port": "UDP Port",
          "udp_interface": "Network Interface"
        }
      },
      "rs485": {
        "title": "RS485 Serial Configuration", 
        "description": "Configure RS485 serial connection",
        "data": {
          "rs485_port": "Serial Port",
          "rs485_baudrate": "Baud Rate",
          "rs485_parity": "Parity"
        }
      },
      "discovery": {
        "title": "Device Discovery",
        "description": "Found {device_count} TIS devices:\n\n{devices}\n\nClick Submit to complete setup."
      }
    },
    "error": {
      "cannot_connect": "Failed to connect via UDP",
      "cannot_connect_rs485": "Failed to connect via RS485", 
      "discovery_failed": "Device discovery failed",
      "unknown": "Unexpected error occurred"
    }
  },
  "options": {
    "step": {
      "init": {
        "title": "TIS Automation Options",
        "data": {
          "scan_interval": "Update Interval (seconds)",
          "enable_debug_logging": "Enable Debug Logging"
        }
      }
    }
  },
  "services": {
    "send_command": {
      "name": "Send TIS Command",
      "description": "Send raw command to TIS device"
    },
    "discover_devices": {
      "name": "Discover Devices", 
      "description": "Scan for new TIS devices"
    },
    "execute_scene": {
      "name": "Execute Scene",
      "description": "Execute TIS scene/scenario"
    },
    "refresh_device": {
      "name": "Refresh Device",
      "description": "Force refresh device state"
    },
    "set_device_parameter": {
      "name": "Set Parameter",
      "description": "Set device parameter"
    }
  }
}
```

### translations/tr.json (Türkçe)

```json
{
  "config": {
    "flow_title": "TIS Ev Otomasyonu",
    "step": {
      "user": {
        "title": "Bağlantı Türü",
        "description": "TIS sisteminize nasıl bağlanacağınızı seçin",
        "data": {
          "connection_type": "Bağlantı Türü"
        }
      },
      "udp": {
        "title": "UDP Ağ Yapılandırması",
        "description": "TIS cihazları için UDP ağ bağlantısını yapılandırın",
        "data": {
          "name": "İsim",
          "udp_port": "UDP Portu",
          "udp_interface": "Ağ Arayüzü"
        }
      },
      "rs485": {
        "title": "RS485 Seri Yapılandırması",
        "description": "RS485 seri bağlantısını yapılandırın", 
        "data": {
          "rs485_port": "Seri Port",
          "rs485_baudrate": "Baud Hızı",
          "rs485_parity": "Parite"
        }
      },
      "discovery": {
        "title": "Cihaz Keşfi",
        "description": "{device_count} TIS cihazı bulundu:\n\n{devices}\n\nKurulumu tamamlamak için Gönder'e tıklayın."
      }
    },
    "error": {
      "cannot_connect": "UDP üzerinden bağlantı kurulamadı",
      "cannot_connect_rs485": "RS485 üzerinden bağlantı kurulamadı",
      "discovery_failed": "Cihaz keşfi başarısız",
      "unknown": "Beklenmeyen hata oluştu"
    }
  },
  "options": {
    "step": {
      "init": {
        "title": "TIS Otomasyon Seçenekleri", 
        "data": {
          "scan_interval": "Güncelleme Aralığı (saniye)",
          "enable_debug_logging": "Debug Kayıt Tutmayı Etkinleştir"
        }
      }
    }
  },
  "services": {
    "send_command": {
      "name": "TIS Komutu Gönder",
      "description": "TIS cihazına ham komut gönder"
    },
    "discover_devices": {
      "name": "Cihaz Keşfet",
      "description": "Yeni TIS cihazları ara"
    },
    "execute_scene": {
      "name": "Sahne Çalıştır", 
      "description": "TIS sahne/senaryo çalıştır"
    },
    "refresh_device": {
      "name": "Cihazı Yenile",
      "description": "Cihaz durumunu zorla yenile"
    },
    "set_device_parameter": {
      "name": "Parametre Ayarla",
      "description": "Cihaz parametresi ayarla" 
    }
  }
}
```

## 📱 Device & Entity Registry Integration

### Device Registry Helper

```python
# device.py

"""Device wrapper for TIS devices."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.entity_registry import RegistryEntry

from .const import DOMAIN, TIS_DEVICE_TYPES

_LOGGER = logging.getLogger(__name__)

class TISDeviceManager:
    """Manage TIS device registry integration."""
    
    def __init__(self, hass, coordinator):
        """Initialize device manager."""
        self.hass = hass
        self.coordinator = coordinator
        
    async def async_update_device_registry(self) -> None:
        """Update device registry with TIS devices."""
        device_registry = self.hass.helpers.device_registry.async_get(self.hass)
        
        for device_id, device in self.coordinator.devices.items():
            device_registry.async_get_or_create(
                config_entry_id=self.coordinator.config_entry.entry_id,
                identifiers={(DOMAIN, device_id)},
                manufacturer="TIS Automation",
                model=device.get_model_description(),
                name=device.model_name,
                sw_version=device.firmware_version,
            )
            
    async def async_remove_device(self, device_id: str) -> None:
        """Remove device from registry."""
        device_registry = self.hass.helpers.device_registry.async_get(self.hass)
        
        device_entry = device_registry.async_get_device(
            identifiers={(DOMAIN, device_id)}
        )
        
        if device_entry:
            device_registry.async_remove_device(device_entry.id)
```

Bu base entity ve services planı:

- ✅ **Unified Base**: Tüm entity'ler için ortak functionality
- ✅ **Rich Services**: Advanced kullanıcılar için raw command API
- ✅ **Multi-language**: Türkçe ve İngilizce destek
- ✅ **Device Registry**: HA device management integration
- ✅ **Service Discovery**: Runtime cihaz keşfi
- ✅ **Error Handling**: Robust service error handling

Bu tamamlandığında TIS Home Assistant entegrasyonun ana mimarisi hazır olacak.
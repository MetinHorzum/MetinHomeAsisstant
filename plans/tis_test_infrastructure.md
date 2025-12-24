
# TIS Test Infrastructure ve Simulator Sistemi

## 🧪 Test Altyapısı Genel Mimari

### Test Klasör Yapısı

```
tests/
├── __init__.py
├── conftest.py                    # Pytest fixtures
├── test_protocol/                 # Protocol tests
│   ├── __init__.py
│   ├── test_packet_builder.py
│   ├── test_crc_calculation.py
│   ├── test_device_discovery.py
│   └── test_communication.py
├── test_homeassistant/            # HA integration tests
│   ├── __init__.py
│   ├── test_config_flow.py
│   ├── test_coordinator.py
│   ├── test_entities.py
│   └── test_services.py
├── test_simulator/                # Simulator tests
│   ├── __init__.py
│   ├── test_mock_devices.py
│   └── test_device_responses.py
├── fixtures/                      # Test data
│   ├── sample_devices.json
│   ├── packet_samples.json
│   └── device_responses/
│       ├── ac_panel_responses.json
│       ├── health_sensor_responses.json
│       └── dimmer_responses.json
└── utils/                        # Test utilities
    ├── __init__.py
    ├── mock_device_factory.py
    ├── packet_generator.py
    └── test_helpers.py
```

## 🎭 TIS Device Simulator

### Mock Device Factory

```python
"""Mock TIS device factory for testing."""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock

from tis_protocol.core import TISPacket, TISCommunicationManager
from tis_protocol.const import TIS_OPCODES

_LOGGER = logging.getLogger(__name__)

@dataclass
class MockDeviceState:
    """Mock device state container."""
    device_id: str
    device_type: int
    online: bool = True
    properties: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.properties is None:
            self.properties = {}

class MockTISDevice:
    """Mock TIS device for testing."""
    
    def __init__(self, device_id: str, device_type: int, **kwargs):
        """Initialize mock device."""
        self.device_id = device_id
        self.device_type = device_type
        self.state = MockDeviceState(device_id, device_type, **kwargs)
        self.response_handlers = {}
        self._setup_default_handlers()
        
    def _setup_default_handlers(self):
        """Setup default response handlers."""
        self.response_handlers[TIS_OPCODES["DISCOVERY_REQUEST"]] = self._handle_discovery
        self.response_handlers[TIS_OPCODES["DEVICE_STATUS"]] = self._handle_status_query
        self.response_handlers[TIS_OPCODES["DEVICE_CONTROL"]] = self._handle_device_control
        self.response_handlers[TIS_OPCODES["FIRMWARE_QUERY"]] = self._handle_firmware_query
        
    async def handle_command(self, packet: TISPacket) -> Optional[TISPacket]:
        """Handle incoming command and generate response."""
        if not self.state.online:
            return None
            
        handler = self.response_handlers.get(packet.op_code)
        if handler:
            return await handler(packet)
            
        return None
        
    async def _handle_discovery(self, packet: TISPacket) -> TISPacket:
        """Handle discovery request."""
        response_data = [
            0x01,  # Device count
            *self.device_id.encode('ascii')[:16].ljust(16, b'\x00'),  # Device ID  
            self.device_type & 0xFF,  # Device type low
            (self.device_type >> 8) & 0xFF,  # Device type high
            0x01, 0x00, 0x00,  # Firmware version
            0x00,  # Status
        ]
        
        return TISPacket(
            device_id=self.device_id,
            op_code=TIS_OPCODES["DISCOVERY_RESPONSE"],
            data=bytes(response_data)
        )
        
    async def _handle_status_query(self, packet: TISPacket) -> TISPacket:
        """Handle status query."""
        # Device-specific status response
        if self.device_type == 0x806C:  # AC Panel
            response_data = self._get_ac_status_data()
        elif self.device_type == 0x8022:  # Health Sensor
            response_data = self._get_health_sensor_data()
        elif self.device_type in [0x0258, 0x0259]:  # Dimmers
            response_data = self._get_dimmer_status_data()
        else:
            response_data = [0x01, 0x00]  # Generic: online, no error
            
        return TISPacket(
            device_id=self.device_id,
            op_code=TIS_OPCODES["DEVICE_STATUS"],
            data=bytes(response_data)
        )
        
    async def _handle_device_control(self, packet: TISPacket) -> TISPacket:
        """Handle device control command."""
        if len(packet.data) >= 2:
            channel = packet.data[0]
            command = packet.data[1]
            
            # Update device state based on command
            if self.device_type in [0x0051, 0x0052]:  # Switches
                self.state.properties[f"channel_{channel}"] = bool(command)
            elif self.device_type in [0x0258, 0x0259]:  # Dimmers
                brightness = packet.data[2] if len(packet.data) > 2 else 0
                self.state.properties[f"channel_{channel}_on"] = bool(command)
                self.state.properties[f"channel_{channel}_brightness"] = brightness
                
        return TISPacket(
            device_id=self.device_id,
            op_code=TIS_OPCODES["DEVICE_UPDATE_RESPONSE"],
            data=bytes([0x00])  # Success
        )
        
    async def _handle_firmware_query(self, packet: TISPacket) -> TISPacket:
        """Handle firmware version query."""
        return TISPacket(
            device_id=self.device_id,
            op_code=TIS_OPCODES["FIRMWARE_RESPONSE"],
            data=b'\x01\x02\x03\x04'  # Mock firmware version
        )
        
    def _get_ac_status_data(self) -> List[int]:
        """Get AC panel status data."""
        return [
            self.state.properties.get("power_state", 1),  # Power
            self.state.properties.get("hvac_mode", 0),    # Mode (cool)
            self.state.properties.get("target_temp", 24), # Target temp
            self.state.properties.get("current_temp", 23),# Current temp
            self.state.properties.get("fan_mode", 1),     # Fan mode
            0x00, 0x00, 0x00  # Padding
        ]
        
    def _get_health_sensor_data(self) -> List[int]:
        """Get health sensor data."""
        # 15-byte health sensor response
        return [
            0x01,  # Status
            0x00, 0x00, 0x00, 0x00,  # Reserved
            0x02, 0x58,  # Lux (600)
            0x00, 0x32,  # Noise (50 dB)
            0x01, 0xF4,  # CO2 (500 ppm)
            0x00, 0x64,  # TVOC (100 ppb)
            self.state.properties.get("temperature", 23),  # Temperature
            self.state.properties.get("humidity", 45),     # Humidity
        ]
        
    def _get_dimmer_status_data(self) -> List[int]:
        """Get dimmer status data."""
        channel = 1  # Default channel
        return [
            channel,
            int(self.state.properties.get(f"channel_{channel}_on", False)),
            self.state.properties.get(f"channel_{channel}_brightness", 0)
        ]

class MockTISSimulator:
    """TIS network simulator for testing."""
    
    def __init__(self):
        """Initialize simulator."""
        self.devices: Dict[str, MockTISDevice] = {}
        self.network_delay = 0.1  # Simulate network latency
        self.packet_loss_rate = 0.0  # No packet loss by default
        
    def add_device(self, device: MockTISDevice):
        """Add device to simulator."""
        self.devices[device.device_id] = device
        
    def remove_device(self, device_id: str):
        """Remove device from simulator."""
        self.devices.pop(device_id, None)
        
    async def handle_packet(self, packet: TISPacket) -> Optional[TISPacket]:
        """Handle incoming packet and generate response."""
        # Simulate network delay
        await asyncio.sleep(self.network_delay)
        
        # Simulate packet loss
        import random
        if random.random() < self.packet_loss_rate:
            return None
            
        # Handle discovery broadcasts
        if packet.op_code == TIS_OPCODES["DISCOVERY_REQUEST"]:
            return await self._handle_discovery_broadcast()
            
        # Handle device-specific commands
        device = self.devices.get(packet.device_id)
        if device:
            return await device.handle_command(packet)
            
        return None
        
    async def _handle_discovery_broadcast(self) -> TISPacket:
        """Handle discovery broadcast."""
        device_list = []
        
        for device in self.devices.values():
            if device.state.online:
                device_info = [
                    *device.device_id.encode('ascii')[:16].ljust(16, b'\x00'),
                    device.device_type & 0xFF,
                    (device.device_type >> 8) & 0xFF,
                    0x01, 0x00, 0x00,  # Firmware version
                ]
                device_list.extend(device_info)
                
        response_data = [len(self.devices)] + device_list
        
        return TISPacket(
            device_id="BROADCAST",
            op_code=TIS_OPCODES["DISCOVERY_RESPONSE"],
            data=bytes(response_data)
        )
        
    def get_device_state(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get device state as dictionary."""
        device = self.devices.get(device_id)
        if device:
            return asdict(device.state)
        return None
        
    def set_device_property(self, device_id: str, key: str, value: Any):
        """Set device property."""
        device = self.devices.get(device_id)
        if device:
            device.state.properties[key] = value
            
    def set_network_conditions(self, delay: float = 0.1, loss_rate: float = 0.0):
        """Set network simulation parameters."""
        self.network_delay = delay
        self.packet_loss_rate = loss_rate

def create_mock_device_from_type(device_id: str, device_type: int) -> MockTISDevice:
    """Create mock device with appropriate default state."""
    device = MockTISDevice(device_id, device_type)
    
    # Set device-specific default properties
    if device_type == 0x806C:  # AC Panel
        device.state.properties.update({
            "power_state": 1,
            "hvac_mode": 0,  # Cool
            "target_temp": 24,
            "current_temp": 23,
            "fan_mode": 1,  # Low
        })
    elif device_type == 0x8022:  # Health Sensor
        device.state.properties.update({
            "temperature": 23,
            "humidity": 45,
            "co2": 400,
            "tvoc": 50,
            "lux": 300,
            "noise": 40,
        })
    elif device_type in [0x0258, 0x0259]:  # Dimmers
        channels = 6 if device_type == 0x0258 else 4
        for i in range(1, channels + 1):
            device.state.properties[f"channel_{i}_on"] = False
            device.state.properties[f"channel_{i}_brightness"] = 0
            
    return device
```

## 🔧 Pytest Fixtures (conftest.py)

### Test Setup ve Teardown

```python
"""Pytest fixtures for TIS testing."""
import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from custom_components.tis_automation.coordinator import TISDataUpdateCoordinator
from tests.utils.mock_device_factory import MockTISSimulator, create_mock_device_from_type

@pytest.fixture
def hass():
    """Create Home Assistant instance."""
    return MagicMock(spec=HomeAssistant)

@pytest.fixture
def mock_config_entry():
    """Create mock config entry."""
    return MagicMock(spec=ConfigEntry, data={
        "udp_enabled": True,
        "udp_port": 6000,
        "rs485_enabled": False,
        "name": "Test TIS System",
    })

@pytest.fixture
async def mock_tis_simulator():
    """Create TIS device simulator."""
    simulator = MockTISSimulator()
    
    # Add sample devices
    devices = [
        ("AC001", 0x806C),  # AC Panel
        ("HEALTH001", 0x8022),  # Health Sensor
        ("DIMMER001", 0x0258),  # 6CH Dimmer
        ("SWITCH001", 0x0051),  # Universal Switch
    ]
    
    for device_id, device_type in devices:
        device = create_mock_device_from_type(device_id, device_type)
        simulator.add_device(device)
        
    yield simulator

@pytest.fixture
async def mock_communication_manager(mock_tis_simulator):
    """Create mock communication manager."""
    with patch('custom_components.tis_automation.TISCommunicationManager') as mock_class:
        mock_instance = AsyncMock()
        mock_class.return_value = mock_instance
        
        # Setup mock methods
        mock_instance.initialize.return_value = True
        mock_instance.discover_devices.return_value = list(mock_tis_simulator.devices.values())
        
        async def mock_send_command(device_id, op_code, data=b''):
            from tis_protocol.core import TISPacket
            packet = TISPacket(device_id=device_id, op_code=op_code, data=data)
            response = await mock_tis_simulator.handle_packet(packet)
            return MagicMock(success=response is not None, data=response.data if response else b'')
            
        mock_instance.send_command = mock_send_command
        
        yield mock_instance

@pytest.fixture
async def mock_coordinator(hass, mock_config_entry, mock_communication_manager, mock_tis_simulator):
    """Create mock coordinator."""
    devices = list(mock_tis_simulator.devices.values())
    
    coordinator = TISDataUpdateCoordinator(
        hass=hass,
        logger=MagicMock(),
        name="test",
        update_interval=30,
        communication_manager=mock_communication_manager,
        devices=devices,
    )
    
    # Mock the actual HA coordinator methods
    coordinator.async_config_entry_first_refresh = AsyncMock()
    coordinator.async_request_refresh = AsyncMock()
    
    yield coordinator

@pytest.fixture
def sample_tis_packets():
    """Sample TIS packets for testing."""
    return {
        "discovery_request": b'\x53\x4D\x41\x52\x54\x43\x4C\x4F\x55\x44\x00\x0E\x00\x00\x00\x00\x00',
        "ac_control": b'\x53\x4D\x41\x52\x54\x43\x4C\x4F\x55\x44\xE0\xEE\x01\x00\x18\xFF\x01',
        "light_on": b'\x53\x4D\x41\x52\x54\x43\x4C\x4F\x55\x44\x00\x31\x01\x01',
        "scene_execute": b'\x53\x4D\x41\x52\x54\x43\x4C\x4F\x55\x44\x00\x31\x01\x01',
    }

@pytest.fixture
def device_response_samples():
    """Sample device responses."""
    return {
        "ac_status": {
            "power_state": True,
            "hvac_mode": "cool",
            "target_temperature": 24,
            "current_temperature": 23,
            "fan_mode": "low",
        },
        "health_sensor": {
            "temperature": 23.5,
            "humidity": 45.2,
            "co2": 421,
            "tvoc": 38,
            "lux": 285,
            "noise": 42,
        },
        "dimmer_status": {
            "channels": {
                1: {"on": True, "brightness": 75},
                2: {"on": False, "brightness": 0},
                3: {"on": True, "brightness": 100},
            }
        }
    }

@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for all tests."""
    pass

@pytest.fixture
async def setup_integration(hass, mock_config_entry, mock_communication_manager):
    """Set up the TIS integration."""
    mock_config_entry.add_to_hass(hass)
    
    with patch('custom_components.tis_automation.TISCommunicationManager', 
               return_value=mock_communication_manager):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        
    yield
    
    # Cleanup
    await hass.config_entries.async_unload(mock_config_entry.entry_id)
```

## 📋 Unit Test Examples

### Protocol Tests

```python
"""Test TIS protocol functions."""
import pytest
from tis_protocol.core import TISPacket, calculate_crc
from tis_protocol.packet_builder import build_discovery_packet, build_control_packet

class TestTISProtocol:
    """Test TIS protocol implementation."""
    
    def test_crc_calculation(self):
        """Test CRC calculation."""
        data = b"SMARTCLOUD"
        crc = calculate_crc(data)
        assert isinstance(crc, int)
        assert 0 <= crc <= 0xFFFF
        
    def test_packet_creation(self):
        """Test TIS packet creation."""
        packet = TISPacket(
            device_id="TEST001",
            op_code=0x0031,
            data=b'\x01\x01'
        )
        
        assert packet.device_id == "TEST001"
        assert packet.op_code == 0x0031
        assert packet.data == b'\x01\x01'
        
    def test_discovery_packet_build(self):
        """Test discovery packet building."""
        packet_data = build_discovery_packet()
        
        assert packet_data.startswith(b'SMARTCLOUD')
        assert len(packet_data) >= 17  # Minimum packet size
        
    def test_control_packet_build(self):
        """Test control packet building."""
        packet_data = build_control_packet("DEVICE001", 0x0031, b'\x01\x01')
        
        assert packet_data.startswith(b'SMARTCLOUD')
        assert b'DEVICE001' in packet_data

class TestDeviceDiscovery:
    """Test device discovery functionality."""
    
    @pytest.mark.asyncio
    async def test_device_discovery(self, mock_tis_simulator):
        """Test device discovery process."""
        devices = list(mock_tis_simulator.devices.values())
        assert len(devices) == 4
        
        # Test discovery response
        from tis_protocol.core import TISPacket
        from tis_protocol.const import TIS_OPCODES
        
        discovery_packet = TISPacket(
            device_id="BROADCAST",
            op_code=TIS_OPCODES["DISCOVERY_REQUEST"],
            data=b''
        )
        
        response = await mock_tis_simulator.handle_packet(discovery_packet)
        assert response is not None
        assert response.op_code == TIS_OPCODES["DISCOVERY_RESPONSE"]
```

### Home Assistant Integration Tests

```python
"""Test Home Assistant integration."""
import pytest
from homeassistant.core import HomeAssistant
from custom_components.tis_automation.const import DOMAIN

class TestConfigFlow:
    """Test configuration flow."""
    
    @pytest.mark.asyncio
    async def test_config_flow_user_step(self, hass: HomeAssistant):
        """Test user configuration step."""
        from custom_components.tis_automation.config_flow import TISConfigFlow
        
        flow = TISConfigFlow()
        flow.hass = hass
        
        result = await flow.async_step_user()
        
        assert result["type"] == "form"
        assert result["step_id"] == "user"
        
    @pytest.mark.asyncio
    async def test_config_flow_udp_step(self, hass: HomeAssistant):
        """Test UDP configuration step."""
        from custom_components.tis_automation.config_flow import TISConfigFlow
        
        flow = TISConfigFlow()
        flow.hass = hass
        flow.data = {"connection_type": "udp"}
        
        user_input = {
            "name": "Test TIS",
            "udp_port": 6000,
            "udp_interface": "0.0.0.0",
        }
        
        with patch('custom_components.tis_automation.config_flow.TISCommunicationManager') as mock_comm:
            mock_comm.return_value.initialize.return_value = True
            
            result = await flow.async_step_udp(user_input)
            
            assert result["type"] == "form"
            assert result["step_id"] == "discovery"

class TestEntities:
    """Test entity implementations."""
    
    @pytest.mark.asyncio
    async def test_switch_entity(self, setup_integration, hass: HomeAssistant):
        """Test switch entity functionality."""
        # Get switch entity
        switch_entity_id = "switch.test_device_switch"
        
        # Test turn on
        await hass.services.async_call(
            "switch", "turn_on", {"entity_id": switch_entity_id}
        )
        await hass.async_block_till_done()
        
        # Verify state
        state = hass.states.get(switch_entity_id)
        assert state.state == "on"
        
    @pytest.mark.asyncio
    async def test_light_entity(self, setup_integration, hass: HomeAssistant):
        """Test light entity functionality."""
        light_entity_id = "light.test_dimmer_ch1"
        
        # Test turn on with brightness
        await hass.services.async_call(
            "light", "turn_on", 
            {"entity_id": light_entity_id, "brightness": 200}
        )
        await hass.async_block_till_done()
        
        # Verify state
        state = hass.states.get(light_entity_id)
        assert state.state == "on"
        assert int(state.attributes["brightness"]) == 200

class TestServices:
    """Test custom services."""
    
    @pytest.mark.asyncio
    async def test_send_command_service(self, setup_integration, hass: HomeAssistant):
        """Test send_command service."""
        await hass.services.async_call(
            DOMAIN,
            "send_command",
            {
                "device_id": "TEST001",
                "opcode": "0x0031",
                "data": "0101"
            }
        )
        await hass.async_block_till_done()
        
    @pytest.mark.asyncio
    async def test_discover_devices_service(self, setup_integration, hass: HomeAssistant):
        """Test discover_devices service."""
        await hass.services.async_call(
            DOMAIN,
            "discover_devices",
            {"timeout": 10}
        )
        await hass.async_block_till_done()
```

## 🚀 Test Çalıştırma Scripts

### run_tests.py

```python
"""Test runner script."""
import sys
import subprocess
from pathlib import Path

def run_tests():
    """Run all tests."""
    test_dir = Path(__file__).parent
    
    # Unit tests
    print("Running unit tests...")
    result = subprocess.run([
        sys.executable, "-m", "pytest",
        str(test_dir / "test_protocol"),
        "-v", "--tb=short"
    ])
    
    if result.returncode != 0:
        print("Unit tests failed!")
        return False
        
    # Integration tests
    print("Running integration tests...")
    result = subprocess.run([
        sys.executable, "-m", "pytest", 
        str(test_dir / "test_homeassistant"),
        "-v", "--tb=short"
    ])
    
    if result.returncode != 0:
        print("Integration tests failed!")
        return False
        
    print("All tests passed!")
    return True

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
```

## 📊 Test Coverage ve Reporting

### pytest.ini

```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
addopts = 
    --strict-markers
    --disable-warnings
    --cov=custom_components.tis_automation
    --cov=tis_protocol
    --cov-report=html:htmlcov
    --cov-report=term-missing
    --cov-fail-under=80

markers =
    asyncio: marks tests as async
    integration: marks tests as integration tests
    unit: marks tests as unit tests
```

Bu test infrastructure:

- ✅ **Complete Mocking**: TIS cihazları ve network simulation
- ✅ **Realistic Testing**: Gerçekçi packet responses ve device behavior
- ✅ **HA Integration**: Home Assistant test patterns
- ✅ **Coverage**: Code coverage reporting
- ✅ **Fixtures**: Reusable test components
- ✅ **Automation**: CI/CD ready test scripts

Bu yapı development phase'ında robust testing sağlayacak.
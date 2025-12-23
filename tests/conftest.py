"""Test fixtures for TIS Home Automation integration."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, Generator

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType

from custom_components.tis_home_automation.const import (
    DOMAIN,
    CONF_LOCAL_IP,
    CONF_COMMUNICATION_TYPE,
    CONF_SERIAL_PORT,
    CONF_BAUDRATE,
    COMMUNICATION_TYPE_UDP,
    COMMUNICATION_TYPE_RS485,
)

# Import TIS protocol mocks
from .mocks.tis_protocol_mock import MockTISDevice, MockTISCommunicationManager
from .mocks.tis_device_simulator import TISDeviceSimulator

@pytest.fixture
def mock_tis_protocol():
    """Mock TIS protocol library."""
    with patch.multiple(
        'custom_components.tis_home_automation',
        TISDevice=MockTISDevice,
        TISCommunicationManager=MockTISCommunicationManager,
        get_local_ip=MagicMock(return_value="192.168.1.100"),
        get_available_serial_ports=MagicMock(return_value=["/dev/ttyUSB0", "/dev/ttyUSB1"]),
    ):
        yield

@pytest.fixture
def mock_config_entry() -> ConfigEntry:
    """Create a mock config entry."""
    return ConfigEntry(
        version=1,
        domain=DOMAIN,
        title="TIS Home Automation Test",
        data={
            CONF_LOCAL_IP: "192.168.1.100",
            CONF_COMMUNICATION_TYPE: COMMUNICATION_TYPE_UDP,
            "port": 6000,
            "discovery_timeout": 30.0,
        },
        source="user",
        unique_id="test_tis_integration",
    )

@pytest.fixture
def mock_serial_config_entry() -> ConfigEntry:
    """Create a mock serial config entry."""
    return ConfigEntry(
        version=1,
        domain=DOMAIN,
        title="TIS Home Automation Serial Test",
        data={
            CONF_COMMUNICATION_TYPE: COMMUNICATION_TYPE_RS485,
            CONF_SERIAL_PORT: "/dev/ttyUSB0",
            CONF_BAUDRATE: 9600,
            "discovery_timeout": 30.0,
        },
        source="user",
        unique_id="test_tis_serial_integration",
    )

@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator."""
    from custom_components.tis_home_automation.coordinator import TISDataUpdateCoordinator
    
    coordinator = AsyncMock(spec=TISDataUpdateCoordinator)
    coordinator.devices = {}
    coordinator.device_states = {}
    coordinator.offline_devices = set()
    coordinator.is_device_online = MagicMock(return_value=True)
    coordinator.get_device_state = MagicMock(return_value={})
    coordinator.send_device_command = AsyncMock(return_value=True)
    coordinator.async_request_refresh = AsyncMock()
    
    return coordinator

@pytest.fixture
def sample_tis_devices() -> Dict[str, MockTISDevice]:
    """Create sample TIS devices for testing."""
    devices = {
        "01FE": MockTISDevice(
            device_id=[0x01, 0xFE],
            device_type=0x0100,  # switch_1gang
            name="Test Switch",
            ip_address="192.168.1.201"
        ),
        "02FE": MockTISDevice(
            device_id=[0x02, 0xFE],
            device_type=0x0110,  # dimmer_1gang  
            name="Test Dimmer",
            ip_address="192.168.1.202"
        ),
        "03FE": MockTISDevice(
            device_id=[0x03, 0xFE],
            device_type=0x0200,  # ac_controller
            name="Test AC",
            ip_address="192.168.1.203"
        ),
        "04FE": MockTISDevice(
            device_id=[0x04, 0xFE],
            device_type=0x0300,  # motion_sensor
            name="Test Motion Sensor",
            ip_address="192.168.1.204"
        ),
        "05FE": MockTISDevice(
            device_id=[0x05, 0xFE],
            device_type=0x0310,  # health_sensor
            name="Test Health Sensor",
            ip_address="192.168.1.205"
        ),
    }
    return devices

@pytest.fixture
def device_simulator(sample_tis_devices) -> TISDeviceSimulator:
    """Create TIS device simulator."""
    simulator = TISDeviceSimulator()
    for device_key, device in sample_tis_devices.items():
        simulator.add_device(device_key, device)
    return simulator

@pytest.fixture
def mock_communication_manager(sample_tis_devices):
    """Create a mock communication manager."""
    manager = MockTISCommunicationManager()
    manager.devices = sample_tis_devices
    return manager

@pytest.fixture
async def setup_integration(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    mock_tis_protocol,
    mock_communication_manager,
) -> ConfigEntry:
    """Set up the TIS integration."""
    # Add the config entry to hass
    hass.config_entries._entries[mock_config_entry.entry_id] = mock_config_entry
    
    # Mock the integration setup
    with patch(
        'custom_components.tis_home_automation.create_communication_manager',
        return_value=mock_communication_manager
    ):
        # Setup the integration
        result = await hass.config_entries.async_setup(mock_config_entry.entry_id)
        assert result is True
    
    return mock_config_entry

@pytest.fixture
def tis_packet_samples():
    """Sample TIS packet data for testing."""
    return {
        "discovery_request": [
            192, 168, 1, 100,  # IP
            83, 77, 65, 82, 84, 67, 76, 79, 85, 68,  # SMARTCLOUD
            170, 170,  # Separator
            11,  # Length
            1, 254,  # Source device
            255, 255,  # Device type
            0, 14,  # Op code (discovery)
            0, 0,  # Target device
            245, 67  # CRC
        ],
        "discovery_response": [
            192, 168, 1, 201,  # IP
            83, 77, 65, 82, 84, 67, 76, 79, 85, 68,  # SMARTCLOUD
            170, 170,  # Separator
            21,  # Length
            1, 254,  # Source device
            1, 0,  # Device type (switch)
            0, 15,  # Op code (discovery response)
            1, 254,  # Target device
            84, 101, 115, 116, 32, 83, 119, 105, 116, 99, 104, 0,  # Device name
            123, 45  # CRC
        ],
        "switch_on": [
            192, 168, 1, 100,  # IP
            83, 77, 65, 82, 84, 67, 76, 79, 85, 68,  # SMARTCLOUD
            170, 170,  # Separator
            11,  # Length
            1, 254,  # Source device
            255, 254,  # Device type
            17, 1,  # Op code (light on)
            1, 254,  # Target device
            78, 89  # CRC
        ],
        "switch_off": [
            192, 168, 1, 100,  # IP
            83, 77, 65, 82, 84, 67, 76, 79, 85, 68,  # SMARTCLOUD
            170, 170,  # Separator
            11,  # Length
            1, 254,  # Source device
            255, 254,  # Device type
            17, 2,  # Op code (light off)
            1, 254,  # Target device
            78, 90  # CRC
        ],
        "dimmer_set": [
            192, 168, 1, 100,  # IP
            83, 77, 65, 82, 84, 67, 76, 79, 85, 68,  # SMARTCLOUD
            170, 170,  # Separator
            12,  # Length
            1, 254,  # Source device
            255, 254,  # Device type
            17, 3,  # Op code (light dimmer)
            2, 254,  # Target device
            50,  # Brightness (50%)
            156, 78  # CRC
        ],
        "ac_control": [
            192, 168, 1, 100,  # IP
            83, 77, 65, 82, 84, 67, 76, 79, 85, 68,  # SMARTCLOUD
            170, 170,  # Separator
            16,  # Length
            1, 254,  # Source device
            255, 254,  # Device type
            224, 237,  # Op code (AC power on)
            3, 254,  # Target device
            0, 24, 0,  # Mode: cool, temp: 24, fan: auto
            198, 45  # CRC
        ],
        "sensor_data": [
            192, 168, 1, 205,  # IP
            83, 77, 65, 82, 84, 67, 76, 79, 85, 68,  # SMARTCLOUD
            170, 170,  # Separator
            25,  # Length
            5, 254,  # Source device
            3, 16,  # Device type (health sensor)
            32, 37,  # Op code (sensor data response)
            1, 254,  # Target device
            1, 44,  # LUX (300)
            0, 45,  # Noise (45 dB)
            1, 144,  # eCO2 (400 ppm)
            0, 10,  # TVOC (10 ppb)
            25,  # Temperature (25°C)
            55,  # Humidity (55%)
            0, 0,  # Reserved
            234, 56  # CRC
        ]
    }

@pytest.fixture
def mock_hass_services():
    """Mock Home Assistant services."""
    services = MagicMock()
    services.async_register = MagicMock()
    services.async_remove = MagicMock()
    services.has_service = MagicMock(return_value=True)
    return services

# Test helper functions
def create_mock_entity_registry():
    """Create mock entity registry."""
    registry = MagicMock()
    registry.async_get = MagicMock(return_value=None)
    registry.async_get_or_create = MagicMock()
    return registry

def create_mock_device_registry():
    """Create mock device registry."""
    registry = MagicMock()
    registry.async_get = MagicMock(return_value=None)
    registry.async_get_device = MagicMock(return_value=None)
    registry.async_get_or_create = MagicMock()
    registry.async_update_device = MagicMock()
    return registry

# State helper functions
def get_entity_state(hass: HomeAssistant, entity_id: str) -> Any:
    """Get entity state from hass."""
    return hass.states.get(entity_id)

def assert_entity_state(hass: HomeAssistant, entity_id: str, expected_state: str):
    """Assert entity state matches expected."""
    state = get_entity_state(hass, entity_id)
    assert state is not None, f"Entity {entity_id} not found"
    assert state.state == expected_state, f"Expected {expected_state}, got {state.state}"

def assert_entity_attribute(hass: HomeAssistant, entity_id: str, attribute: str, expected_value: Any):
    """Assert entity attribute matches expected."""
    state = get_entity_state(hass, entity_id)
    assert state is not None, f"Entity {entity_id} not found"
    assert attribute in state.attributes, f"Attribute {attribute} not found in {entity_id}"
    assert state.attributes[attribute] == expected_value, \
        f"Expected {expected_value}, got {state.attributes[attribute]}"

# Async test helpers
async def trigger_coordinator_update(coordinator):
    """Trigger a coordinator update."""
    if hasattr(coordinator, 'async_request_refresh'):
        await coordinator.async_request_refresh()
    elif hasattr(coordinator, '_async_update_data'):
        await coordinator._async_update_data()

async def wait_for_entity_state(hass: HomeAssistant, entity_id: str, expected_state: str, timeout: float = 5.0):
    """Wait for entity to reach expected state."""
    import asyncio
    
    start_time = asyncio.get_event_loop().time()
    while asyncio.get_event_loop().time() - start_time < timeout:
        state = get_entity_state(hass, entity_id)
        if state and state.state == expected_state:
            return True
        await asyncio.sleep(0.1)
    
    return False

# Error simulation helpers
class TISCommunicationErrorSimulator:
    """Simulate TIS communication errors for testing."""
    
    def __init__(self):
        self.connection_errors = []
        self.timeout_errors = []
        self.crc_errors = []
        self.device_offline = []
    
    def simulate_connection_error(self, device_id: str):
        """Simulate connection error for device."""
        self.connection_errors.append(device_id)
    
    def simulate_timeout_error(self, device_id: str):
        """Simulate timeout error for device."""
        self.timeout_errors.append(device_id)
    
    def simulate_crc_error(self, device_id: str):
        """Simulate CRC error for device."""
        self.crc_errors.append(device_id)
    
    def set_device_offline(self, device_id: str):
        """Set device as offline."""
        self.device_offline.append(device_id)
    
    def clear_all_errors(self):
        """Clear all simulated errors."""
        self.connection_errors.clear()
        self.timeout_errors.clear()
        self.crc_errors.clear()
        self.device_offline.clear()

@pytest.fixture
def error_simulator():
    """Create error simulator."""
    return TISCommunicationErrorSimulator()

# Performance testing helpers
class PerformanceTimer:
    """Simple performance timer for tests."""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        import time
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, *args):
        import time
        self.end_time = time.perf_counter()
    
    @property
    def elapsed(self) -> float:
        """Get elapsed time in seconds."""
        if self.start_time is None or self.end_time is None:
            return 0.0
        return self.end_time - self.start_time

@pytest.fixture
def performance_timer():
    """Create performance timer."""
    return PerformanceTimer
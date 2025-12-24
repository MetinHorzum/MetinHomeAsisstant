"""
Mock devices for TIS Home Automation testing.
Used when no real TIS devices are available.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from .tis_protocol.core import TISDevice, DeviceType

_LOGGER = logging.getLogger(__name__)

class MockTISDevice:
    """Mock TIS device for testing."""
    
    def __init__(self, device_id: str, device_type: str, name: str, ip_address: str = "127.0.0.1"):
        self.device_id = device_id
        self.device_type = device_type
        self.name = name
        self.ip_address = ip_address
        self.last_seen = datetime.now()
        self.is_online = True
        self.state = {"power": False, "brightness": 100, "temperature": 22.0}
    
    def to_tis_device(self) -> TISDevice:
        """Convert to TISDevice object."""
        return TISDevice(
            device_id=self.device_id,
            device_type=DeviceType(int(self.device_type, 16)),
            ip_address=self.ip_address,
            last_seen=self.last_seen,
            is_online=self.is_online,
            raw_data=self.state
        )

# Mock device definitions
MOCK_DEVICES = [
    MockTISDevice("0001", "0101", "Mock Switch 1", "192.168.1.100"),
    MockTISDevice("0002", "0102", "Mock Switch 2-Gang", "192.168.1.101"), 
    MockTISDevice("0003", "0201", "Mock Dimmer Light", "192.168.1.102"),
    MockTISDevice("0004", "0301", "Mock Temperature Sensor", "192.168.1.103"),
    MockTISDevice("0005", "0401", "Mock Motion Sensor", "192.168.1.104"),
    MockTISDevice("0006", "0501", "Mock AC Controller", "192.168.1.105"),
]

def get_mock_devices() -> List[MockTISDevice]:
    """Get list of mock devices."""
    _LOGGER.debug(f"Returning {len(MOCK_DEVICES)} mock devices")
    return MOCK_DEVICES

def create_mock_device_data() -> Dict[str, Any]:
    """Create mock device data for coordinator."""
    devices = {}
    for mock_device in MOCK_DEVICES:
        devices[mock_device.device_id] = {
            "device": mock_device.to_tis_device(),
            "last_update": datetime.now(),
            "state": mock_device.state.copy()
        }
    
    _LOGGER.info(f"Created mock data for {len(devices)} devices")
    return devices

def is_mock_mode_enabled() -> bool:
    """Check if mock mode should be enabled."""
    # Mock mode aktif edilebilir - bu gerçek cihaz yoksa fallback
    return True  # Şimdilik her zaman aktif

class MockCommunicationManager:
    """Mock communication manager for testing."""
    
    def __init__(self):
        self.devices = {dev.device_id: dev for dev in get_mock_devices()}
        _LOGGER.info("Mock Communication Manager initialized")
    
    async def discover_devices(self, timeout: float = 30.0) -> List[TISDevice]:
        """Mock device discovery."""
        _LOGGER.info(f"Mock discovery started (timeout: {timeout}s)")
        await asyncio.sleep(1)  # Simulate discovery delay
        
        tis_devices = [dev.to_tis_device() for dev in self.devices.values()]
        _LOGGER.info(f"Mock discovery found {len(tis_devices)} devices")
        return tis_devices
    
    async def send_command(self, device_id: str, command: bytes) -> Optional[bytes]:
        """Mock command sending."""
        if device_id in self.devices:
            _LOGGER.debug(f"Mock command sent to {device_id}: {command.hex()}")
            return b'\x00\x0F' + bytes.fromhex(device_id) + b'\x01'  # Mock response
        return None
    
    async def close(self):
        """Mock close connection."""
        _LOGGER.debug("Mock communication manager closed")
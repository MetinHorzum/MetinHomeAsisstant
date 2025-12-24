"""Mock TIS protocol objects for testing."""
from __future__ import annotations

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from unittest.mock import AsyncMock, MagicMock

_LOGGER = logging.getLogger(__name__)

class MockTISDevice:
    """Mock TIS device for testing."""
    
    def __init__(
        self,
        device_id: List[int],
        device_type: int,
        name: str,
        ip_address: str = "",
        source_address: Any = None,
        firmware_version: str = "1.0.0"
    ):
        self.device_id = device_id
        self.device_type = device_type
        self.name = name
        self.ip_address = ip_address
        self.source_address = source_address
        self.firmware_version = firmware_version
        
        # Device state simulation
        self._state = {
            "online": True,
            "power": "off",
            "brightness": 0,
            "temperature": 24,
            "humidity": 50,
            "motion": False,
            "contact": False,
            "switches": [],
            "dimmers": [],
            "ac": {},
            "sensors": {},
        }
    
    def get_state(self) -> Dict[str, Any]:
        """Get current device state."""
        return self._state.copy()
    
    def set_state(self, key: str, value: Any):
        """Set device state value."""
        self._state[key] = value
    
    def update_state(self, state_update: Dict[str, Any]):
        """Update device state with multiple values."""
        self._state.update(state_update)

class MockTISTransport:
    """Mock TIS transport for testing."""
    
    def __init__(self, transport_type: str = "udp"):
        self.transport_type = transport_type
        self.connected = False
        self.timeout = 5.0
        self._response_callbacks: Dict[int, Callable] = {}
        self._sent_packets: List[bytes] = []
        self._receive_queue: List[bytes] = []
    
    async def connect(self) -> bool:
        """Mock connect."""
        self.connected = True
        return True
    
    async def disconnect(self) -> bool:
        """Mock disconnect."""
        self.connected = False
        return True
    
    async def send_packet(self, packet: List[int]) -> bool:
        """Mock send packet."""
        if not self.connected:
            return False
        
        self._sent_packets.append(bytes(packet))
        return True
    
    async def receive_packet(self, timeout: Optional[float] = None) -> Optional[bytes]:
        """Mock receive packet."""
        if not self.connected or not self._receive_queue:
            return None
        
        return self._receive_queue.pop(0)
    
    async def broadcast_discovery(self, source_ip: str) -> bool:
        """Mock discovery broadcast."""
        return self.connected
    
    def register_response_callback(self, op_code: int, callback: Callable):
        """Register response callback."""
        self._response_callbacks[op_code] = callback
    
    def unregister_response_callback(self, op_code: int):
        """Unregister response callback."""
        if op_code in self._response_callbacks:
            del self._response_callbacks[op_code]
    
    def add_received_packet(self, packet: bytes):
        """Add packet to receive queue."""
        self._receive_queue.append(packet)
    
    def get_sent_packets(self) -> List[bytes]:
        """Get list of sent packets."""
        return self._sent_packets.copy()
    
    def clear_sent_packets(self):
        """Clear sent packets list."""
        self._sent_packets.clear()

class MockTISCommunicationManager:
    """Mock TIS communication manager for testing."""
    
    def __init__(self):
        self.transports: List[MockTISTransport] = []
        self.devices: Dict[str, MockTISDevice] = {}
        self.discovered_devices: Dict[str, MockTISDevice] = {}
        self.active_transport: Optional[MockTISTransport] = None
        self._discovery_callbacks: List[Callable] = []
        self._discovery_enabled = True
        self._command_responses = {}
    
    def add_transport(self, transport: MockTISTransport):
        """Add a transport."""
        self.transports.append(transport)
        if not self.active_transport:
            self.active_transport = transport
    
    def add_discovery_callback(self, callback: Callable):
        """Add discovery callback."""
        self._discovery_callbacks.append(callback)
    
    async def connect_all(self) -> Dict[str, bool]:
        """Connect all transports."""
        results = {}
        for i, transport in enumerate(self.transports):
            transport_name = f"{transport.transport_type}_{i}"
            results[transport_name] = await transport.connect()
        return results
    
    async def disconnect_all(self) -> Dict[str, bool]:
        """Disconnect all transports."""
        results = {}
        for i, transport in enumerate(self.transports):
            transport_name = f"{transport.transport_type}_{i}"
            results[transport_name] = await transport.disconnect()
        return results
    
    async def discover_devices(
        self, 
        source_ip: str = "192.168.1.100",
        timeout: float = 30.0
    ) -> Dict[str, MockTISDevice]:
        """Mock device discovery."""
        if not self._discovery_enabled:
            return {}
        
        # Simulate discovery delay
        await asyncio.sleep(0.1)
        
        # Return pre-configured devices
        discovered = {}
        for device_key, device in self.devices.items():
            discovered[device_key] = device
            
            # Notify callbacks
            for callback in self._discovery_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(device)
                    else:
                        callback(device)
                except Exception as e:
                    _LOGGER.error(f"Discovery callback error: {e}")
        
        self.discovered_devices.update(discovered)
        return discovered
    
    async def send_to_device(
        self,
        device_id: List[int],
        op_code: List[int],
        source_ip: str = "192.168.1.100",
        additional_data: List[int] = None,
        transport: Optional[MockTISTransport] = None
    ) -> bool:
        """Mock send to device."""
        if not self.active_transport or not self.active_transport.connected:
            return False
        
        # Simulate command processing
        device_key = f"{device_id[0]:02X}{device_id[1]:02X}"
        if device_key in self.devices:
            device = self.devices[device_key]
            
            # Process command and update device state
            self._process_command(device, op_code, additional_data or [])
            
            # Simulate network delay
            await asyncio.sleep(0.01)
            return True
        
        return False
    
    def _process_command(self, device: MockTISDevice, op_code: List[int], additional_data: List[int]):
        """Process command and update device state."""
        op_value = (op_code[0] << 8) | op_code[1]
        
        # Switch/Light commands
        if op_value == 0x1101:  # Light on
            device.set_state("power", "on")
            if len(additional_data) > 0:
                gang_index = additional_data[0]
                switches = device.get_state().get("switches", [])
                while len(switches) <= gang_index:
                    switches.append({"state": "off"})
                switches[gang_index]["state"] = "on"
                device.set_state("switches", switches)
        
        elif op_value == 0x1102:  # Light off
            device.set_state("power", "off")
            if len(additional_data) > 0:
                gang_index = additional_data[0]
                switches = device.get_state().get("switches", [])
                while len(switches) <= gang_index:
                    switches.append({"state": "off"})
                switches[gang_index]["state"] = "off"
                device.set_state("switches", switches)
        
        elif op_value == 0x1103:  # Light dimmer
            device.set_state("power", "on")
            if len(additional_data) > 0:
                brightness = additional_data[-1]  # Last data is brightness
                device.set_state("brightness", brightness)
                
                # Update dimmer state
                gang_index = additional_data[0] if len(additional_data) > 1 else 0
                dimmers = device.get_state().get("dimmers", [])
                while len(dimmers) <= gang_index:
                    dimmers.append({"state": "off", "brightness": 0})
                dimmers[gang_index] = {"state": "on", "brightness": brightness}
                device.set_state("dimmers", dimmers)
        
        # AC commands
        elif op_value == 0xE0ED:  # AC power on
            ac_state = {"power": "on", "mode": "auto", "temperature": 24, "fan_speed": 0}
            if len(additional_data) > 0:
                ac_state["mode"] = ["cool", "heat", "fan", "auto"][additional_data[0] % 4]
            device.set_state("ac", ac_state)
        
        elif op_value == 0xE0EE:  # AC power off
            ac_state = device.get_state().get("ac", {})
            ac_state["power"] = "off"
            device.set_state("ac", ac_state)
        
        elif op_value == 0xE0EF:  # AC set temperature
            if len(additional_data) > 0:
                ac_state = device.get_state().get("ac", {})
                ac_state["temperature"] = additional_data[0]
                device.set_state("ac", ac_state)
    
    def add_device(self, device_key: str, device: MockTISDevice):
        """Add device to manager."""
        self.devices[device_key] = device
    
    def set_discovery_enabled(self, enabled: bool):
        """Enable/disable discovery."""
        self._discovery_enabled = enabled
    
    def simulate_device_response(self, device_key: str, response_data: Dict[str, Any]):
        """Simulate device response."""
        if device_key in self.devices:
            self.devices[device_key].update_state(response_data)
    
    def get_transport_packets(self) -> List[bytes]:
        """Get all sent packets from transports."""
        packets = []
        for transport in self.transports:
            packets.extend(transport.get_sent_packets())
        return packets

# Mock helper functions
def create_mock_udp_transport() -> MockTISTransport:
    """Create mock UDP transport."""
    return MockTISTransport("udp")

def create_mock_rs485_transport() -> MockTISTransport:
    """Create mock RS485 transport."""
    return MockTISTransport("rs485")

async def create_mock_communication_manager(
    udp_config: Optional[Dict] = None,
    serial_config: Optional[Dict] = None
) -> MockTISCommunicationManager:
    """Create mock communication manager."""
    manager = MockTISCommunicationManager()
    
    if udp_config:
        udp_transport = create_mock_udp_transport()
        manager.add_transport(udp_transport)
    
    if serial_config:
        rs485_transport = create_mock_rs485_transport()
        manager.add_transport(rs485_transport)
    
    return manager

# Mock protocol functions
def mock_get_local_ip() -> str:
    """Mock get local IP."""
    return "192.168.1.100"

def mock_get_available_serial_ports() -> List[str]:
    """Mock get available serial ports."""
    return ["/dev/ttyUSB0", "/dev/ttyUSB1", "COM3", "COM4"]

def mock_build_packet(
    operation_code: List[int],
    ip_address: str,
    device_id: List[int] = None,
    source_device_id: List[int] = None,
    device_type: List[int] = None,
    additional_packets: List[int] = None,
    header: str = "SMARTCLOUD"
) -> List[int]:
    """Mock build packet function."""
    # Simple mock packet structure
    packet = []
    
    # Add IP
    ip_parts = [int(part) for part in ip_address.split(".")]
    packet.extend(ip_parts)
    
    # Add header
    packet.extend([ord(c) for c in header])
    
    # Add separator
    packet.extend([0xAA, 0xAA])
    
    # Add length (calculate based on content)
    length = 11 + len(additional_packets or [])
    packet.append(length)
    
    # Add source device
    packet.extend(source_device_id or [0x01, 0xFE])
    
    # Add device type
    packet.extend(device_type or [0xFF, 0xFE])
    
    # Add operation code
    packet.extend(operation_code)
    
    # Add target device
    packet.extend(device_id or [0x00, 0x00])
    
    # Add additional data
    if additional_packets:
        packet.extend(additional_packets)
    
    # Add mock CRC
    packet.extend([0x12, 0x34])
    
    return packet

def mock_parse_smartcloud_packet(packet_data: bytes) -> Dict[str, Any]:
    """Mock parse SMARTCLOUD packet."""
    if len(packet_data) < 29:
        return {"valid": False, "error": "Packet too short"}
    
    try:
        # Extract basic packet components
        ip = f"{packet_data[0]}.{packet_data[1]}.{packet_data[2]}.{packet_data[3]}"
        header = packet_data[4:14].decode('ascii', errors='ignore')
        
        if header != "SMARTCLOUD":
            return {"valid": False, "error": "Invalid header"}
        
        length = packet_data[16]
        source_device = [packet_data[17], packet_data[18]]
        device_type = (packet_data[19] << 8) | packet_data[20]
        op_code = (packet_data[21] << 8) | packet_data[22]
        target_device = [packet_data[23], packet_data[24]]
        
        additional_data = b""
        if length > 11:
            additional_data = packet_data[25:25 + (length - 11)]
        
        return {
            "valid": True,
            "ip": ip,
            "header": header,
            "length": length,
            "source_device": source_device,
            "device_type": device_type,
            "op_code": op_code,
            "target_device": target_device,
            "additional_data": additional_data,
            "crc": 0x1234,  # Mock CRC
            "crc_valid": True,
            "raw_data": packet_data
        }
        
    except Exception as e:
        return {"valid": False, "error": str(e)}

# Mock TIS protocol exceptions
class MockTISCommunicationError(Exception):
    """Mock TIS communication error."""
    pass

class MockTISTimeoutError(MockTISCommunicationError):
    """Mock TIS timeout error."""
    pass

class MockTISConnectionError(MockTISCommunicationError):
    """Mock TIS connection error."""
    pass

# Export all mock classes and functions
__all__ = [
    "MockTISDevice",
    "MockTISTransport", 
    "MockTISCommunicationManager",
    "create_mock_udp_transport",
    "create_mock_rs485_transport",
    "create_mock_communication_manager",
    "mock_get_local_ip",
    "mock_get_available_serial_ports",
    "mock_build_packet",
    "mock_parse_smartcloud_packet",
    "MockTISCommunicationError",
    "MockTISTimeoutError",
    "MockTISConnectionError",
]
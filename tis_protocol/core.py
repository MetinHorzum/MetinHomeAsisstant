"""
TIS Protocol Core Library
Core data structures and protocol implementations for TIS Home Automation systems.
"""
from __future__ import annotations

import logging
import struct
import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, Callable
from dataclasses import dataclass, field
from enum import Enum

_LOGGER = logging.getLogger(__name__)

# ================== CORE CONSTANTS ==================

class TISOpCode(Enum):
    """TIS Protocol Operation Codes"""
    # Discovery & Network
    DISCOVERY_REQUEST = 0x000E
    DISCOVERY_RESPONSE = 0x000F
    DEVICE_INFO_REQUEST = 0x0031
    DEVICE_INFO_RESPONSE = 0x0032
    DEVICE_UPDATE_REQUEST = 0x0033
    DEVICE_UPDATE_RESPONSE = 0x0034
    
    # AC Control
    AC_CONTROL = 0xE0EE
    AC_STATUS = 0xE0ED
    AC_QUERY = 0xA12E
    AC_RESPONSE = 0xA12F
    
    # Firmware & System
    FIRMWARE_QUERY = 0xEFFD
    FIRMWARE_RESPONSE = 0xEFFE
    UNIQUE_ID_QUERY = 0xF003
    UNIQUE_ID_RESPONSE = 0xF004
    
    # Status & Monitoring
    STATUS_QUERY = 0x0280
    STATUS_RESPONSE = 0x0281
    SENSOR_QUERY = 0x2024
    SENSOR_RESPONSE = 0x2025
    
    # Health Sensors (Air Quality)
    HEALTH_SENSOR_REQUEST = 0x2024
    HEALTH_SENSOR_RESPONSE = 0x2025
    
    # Floor Heating
    FLOOR_UPDATE_REQUEST = 0x1944
    FLOOR_BINARY_FEEDBACK = 0x1945
    FLOOR_CONTROL_COMMAND = 0xE3D8
    
    # Binary Feedback
    BINARY_FEEDBACK = 0xE3D9
    AUTO_BINARY_FEEDBACK = 0xDC22
    
    # Temperature
    TEMPERATURE_REQUEST = 0xE3E7
    TEMPERATURE_FEEDBACK = 0xE3E8
    
    # Energy Meter
    ENERGY_METER_REQUEST = 0x2010
    ENERGY_METER_FEEDBACK = 0x2011
    
    # Security
    SECURITY_CONTROL = 0x0104
    SECURITY_UPDATE_REQUEST = 0x011E
    SECURITY_UPDATE_RESPONSE = 0x011F
    
    # SMARTCLOUD Specific
    STATUS_RESPONSE_AR = 0x4152  # "AR"
    SMART_DEVICE_SD = 0x5344     # "SD"
    OK_RESPONSE = 0x4B4F         # "OK"
    ERROR_RESPONSE = 0x4552      # "ER"
    
    # Broadcast
    BROADCAST_COMMAND = 0xE0EE

class TISDeviceType(Enum):
    """TIS Device Types (from reverse engineering)"""
    # Lighting
    SINGLE_CHANNEL_LIGHTING = 0x0001
    DIMMER_6CH_2A = 0x0258
    DIMMER_4CH_3A = 0x0259
    DIMMER_2CH_6A = 0x025A
    
    # Control Panels & Switches
    SECURITY_MODULE = 0x0030
    CURTAIN_SWITCH = 0x0041
    UNIVERSAL_SWITCH_TYPE1 = 0x0051
    PANEL_CONTROL_AC = 0x0052
    UNIVERSAL_SWITCH_TYPE3 = 0x0053
    UNIVERSAL_SWITCH_TYPE4 = 0x0054
    SCENE_SWITCH = 0x0056
    
    # Climate Control
    TIS_MER_AC4G_PB = 0x806C  # AC Control Panel
    HVAC6_3A_T = 0x0077
    
    # Sensors
    TIS_HEALTH_CM = 0x8022    # Health Sensor
    TIS_4DI_IN = 0x0076       # Digital Input
    TIS_PIR_CM = 0x0085       # PIR Sensor
    
    # Audio & Entertainment
    AUDIO_PLAYER_MODULE = 0x0085
    
    # Generic fallback
    LIGHT_DIMMER_GENERIC = 0xFFFE
    CONTROL_PANEL_GENERIC = 0x0000

# TIS Device Type Names Mapping
TIS_DEVICE_NAMES = {
    # Lighting Devices
    0x0001: "Single Channel Lighting",
    
    # Control Panels & Switches  
    0x0030: "Security Module",
    0x0041: "Curtain Switch",
    0x0051: "Universal Switch Type 1",
    0x0052: "Panel Control AC", 
    0x0053: "Universal Switch Type 3",
    0x0054: "Universal Switch Type 4",
    0x0056: "Scene Switch",
    
    # Audio & Entertainment
    0x0085: "Audio Player Module",
    
    # Advanced devices from analysis
    0x0076: "TIS-4DI-IN (4 Zone Digital Input)",
    0x0077: "HVAC6-3A-T (HVAC Air Condition)",
    0x0132: "TIS-IR-CUR (IR Emitter)",
    0x0135: "ES-10F-CM (10 Functions Sensor)",
    0x01A8: "RLY-4CH-10A (Relay 4ch 10A)",
    0x01AA: "VLC-6CH-3A (Valve Controller 6CH)",
    0x01AC: "RLY-8CH-16A (Relay 8ch 16A)",
    0x01B8: "VLC-12CH-10A (Valve Controller 12CH)",
    0x0258: "DIM-6CH-2A (Dimmer 6ch 2A)",
    0x0259: "DIM-4CH-3A (Dimmer 4ch 3A)",
    0x025A: "DIM-2CH-6A (Dimmer 2ch 6A)",
    0x0454: "TIS-AUT-TMR (Automation Timer)",
    0x04B1: "IP-COM-PORT-OLD",
    0x0BE9: "TIS-SEC-SM (Security Module)",
    
    # Mercury Series  
    0x806B: "TIS-MER-8G-PB (Mercury 8G Panel)",
    0x806C: "TIS-MER-AC4G-PB (Mercury AC 4G Panel)",
    
    # Health & Environmental Sensors
    0x8022: "TIS-HEALTH-CM (Health Sensor)",
    0x80AE: "TIS-HEALTH-CM-RADAR",
    0x80B0: "TIS-RADAR-SENSOR",
    
    # Generic fallback
    0xFFFE: "Light Dimmer (Generic)",
    0x0000: "Control Panel (Generic)"
}

# CRC Lookup Table (from TIS documentation)
CRC_TABLE = [
    0x0000, 0x1021, 0x2042, 0x3063, 0x4084, 0x50A5, 0x60C6, 0x70E7,
    0x8108, 0x9129, 0xA14A, 0xB16B, 0xC18C, 0xD1AD, 0xE1CE, 0xF1EF,
    0x1231, 0x0210, 0x3273, 0x2252, 0x52B5, 0x4294, 0x72F7, 0x62D6,
    0x9339, 0x8318, 0xB37B, 0xA35A, 0xD3BD, 0xC39C, 0xF3FF, 0xE3DE,
    0x2462, 0x3443, 0x0420, 0x1401, 0x64E6, 0x74C7, 0x44A4, 0x5485,
    0xA56A, 0xB54B, 0x8528, 0x9509, 0xE5EE, 0xF5CF, 0xC5AC, 0xD58D,
    0x3653, 0x2672, 0x1611, 0x0630, 0x76D7, 0x66F6, 0x5695, 0x46B4,
    0xB75B, 0xA77A, 0x9719, 0x8738, 0xF7DF, 0xE7FE, 0xD79D, 0xC7BC,
    0x48C4, 0x58E5, 0x6886, 0x78A7, 0x0840, 0x1861, 0x2802, 0x3823,
    0xC9CC, 0xD9ED, 0xE98E, 0xF9AF, 0x8948, 0x9969, 0xA90A, 0xB92B,
    0x5AF5, 0x4AD4, 0x7AB7, 0x6A96, 0x1A71, 0x0A50, 0x3A33, 0x2A12,
    0xDBFD, 0xCBDC, 0xFBBF, 0xEB9E, 0x9B79, 0x8B58, 0xBB3B, 0xAB1A,
    0x6CA6, 0x7C87, 0x4CE4, 0x5CC5, 0x2C22, 0x3C03, 0x0C60, 0x1C41,
    0xEDAE, 0xFD8F, 0xCDEC, 0xDDCD, 0xAD2A, 0xBD0B, 0x8D68, 0x9D49,
    0x7E97, 0x6EB6, 0x5ED5, 0x4EF4, 0x3E13, 0x2E32, 0x1E51, 0x0E70,
    0xFF9F, 0xEFBE, 0xDFDD, 0xCFFC, 0xBF1B, 0xAF3A, 0x9F59, 0x8F78,
    0x9188, 0x81A9, 0xB1CA, 0xA1EB, 0xD10C, 0xC12D, 0xF14E, 0xE16F,
    0x1080, 0x00A1, 0x30C2, 0x20E3, 0x5004, 0x4025, 0x7046, 0x6067,
    0x83B9, 0x9398, 0xA3FB, 0xB3DA, 0xC33D, 0xD31C, 0xE37F, 0xF35E,
    0x02B1, 0x1290, 0x22F3, 0x32D2, 0x4235, 0x5214, 0x6277, 0x7256,
    0xB5EA, 0xA5CB, 0x95A8, 0x8589, 0xF56E, 0xE54F, 0xD52C, 0xC50D,
    0x34E2, 0x24C3, 0x14A0, 0x0481, 0x7466, 0x6447, 0x5424, 0x4405,
    0xA7DB, 0xB7FA, 0x8799, 0x97B8, 0xE75F, 0xF77E, 0xC71D, 0xD73C,
    0x26D3, 0x36F2, 0x0691, 0x16B0, 0x6657, 0x7676, 0x4615, 0x5634,
    0xD94C, 0xC96D, 0xF90E, 0xE92F, 0x99C8, 0x89E9, 0xB98A, 0xA9AB,
    0x5844, 0x4865, 0x7806, 0x6827, 0x18C0, 0x08E1, 0x3882, 0x28A3,
    0xCB7D, 0xDB5C, 0xEB3F, 0xFB1E, 0x8BF9, 0x9BD8, 0xABBB, 0xBB9A,
    0x4A75, 0x5A54, 0x6A37, 0x7A16, 0x0AF1, 0x1AD0, 0x2AB3, 0x3A92,
    0xFD2E, 0xED0F, 0xDD6C, 0xCD4D, 0xBDAA, 0xAD8B, 0x9DE8, 0x8DC9,
    0x7C26, 0x6C07, 0x5C64, 0x4C45, 0x3CA2, 0x2C83, 0x1CE0, 0x0CC1,
    0xEF1F, 0xFF3E, 0xCF5D, 0xDF7C, 0xAF9B, 0xBFBA, 0x8FD9, 0x9FF8,
    0x6E17, 0x7E36, 0x4E55, 0x5E74, 0x2E93, 0x3EB2, 0x0ED1, 0x1EF0
]

# ================== CORE DATA STRUCTURES ==================

@dataclass
class TISPacket:
    """TIS Protocol Packet Structure"""
    # Packet components
    ip_address: str = ""                    # Source IP (for UDP)
    header: str = "SMARTCLOUD"              # Protocol header
    length: int = 0                         # Payload length
    source_device_id: List[int] = field(default_factory=lambda: [0x01, 0xFE])
    device_type: int = 0xFFFE              # Device type
    op_code: int = 0x0000                  # Operation code
    target_device_id: List[int] = field(default_factory=lambda: [0xFF, 0xFF])
    additional_data: bytes = b''            # Payload data
    crc: int = 0                           # CRC checksum
    
    # Metadata
    timestamp: Optional[datetime] = None
    transport: str = "udp"                 # "udp" or "rs485"
    raw_data: Optional[bytes] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    @property
    def source_address(self) -> str:
        """Get source address as string (subnet.device)"""
        if len(self.source_device_id) >= 2:
            return f"{self.source_device_id[0]}.{self.source_device_id[1]}"
        return "0.0"
    
    @property
    def target_address(self) -> str:
        """Get target address as string (subnet.device)"""
        if len(self.target_device_id) >= 2:
            return f"{self.target_device_id[0]}.{self.target_device_id[1]}"
        return "0.0"
        
    @property
    def is_broadcast(self) -> bool:
        """Check if this is a broadcast packet"""
        return (len(self.target_device_id) >= 2 and 
                self.target_device_id[0] == 0xFF and 
                self.target_device_id[1] == 0xFF)
    
    @property
    def device_type_name(self) -> str:
        """Get human readable device type name"""
        return TIS_DEVICE_NAMES.get(self.device_type, f"Unknown (0x{self.device_type:04X})")
    
    @property
    def op_code_name(self) -> str:
        """Get operation code name"""
        try:
            return TISOpCode(self.op_code).name
        except ValueError:
            return f"Unknown (0x{self.op_code:04X})"
    
    def to_bytes(self) -> bytes:
        """Convert packet to bytes for transmission"""
        try:
            # Build packet using existing build_packet function
            from . import build_packet  # Import from helper module
            
            # Convert IP address to bytes
            ip_bytes = []
            if self.ip_address:
                ip_bytes = [int(part) for part in self.ip_address.split(".")]
            else:
                ip_bytes = [192, 168, 1, 100]  # Default IP
            
            # Convert additional_data to list
            additional_list = list(self.additional_data) if self.additional_data else []
            
            packet_data = build_packet(
                operation_code=[(self.op_code >> 8) & 0xFF, self.op_code & 0xFF],
                ip_address=self.ip_address or "192.168.1.100",
                device_id=self.target_device_id,
                source_device_id=self.source_device_id, 
                device_type=[(self.device_type >> 8) & 0xFF, self.device_type & 0xFF],
                additional_packets=additional_list,
                header=self.header
            )
            
            return bytes(packet_data)
            
        except Exception as e:
            _LOGGER.error(f"Failed to convert packet to bytes: {e}")
            return b''
    
    @classmethod
    def from_bytes(cls, data: bytes, transport: str = "udp") -> Optional['TISPacket']:
        """Create TISPacket from raw bytes"""
        try:
            from . import parse_smartcloud_packet  # Import from helper module
            
            parsed = parse_smartcloud_packet(data)
            if not parsed or not parsed.get('valid', False):
                return None
            
            # Create packet from parsed data
            packet = cls(
                ip_address=parsed.get('ip', ''),
                header=parsed.get('header', 'SMARTCLOUD'),
                length=parsed.get('length', 0),
                source_device_id=parsed.get('source_device', [0, 0]),
                device_type=parsed.get('device_type', 0xFFFE),
                op_code=parsed.get('op_code', 0x0000),
                target_device_id=parsed.get('target_device', [0, 0]),
                additional_data=parsed.get('additional_data', b''),
                crc=parsed.get('crc', 0),
                transport=transport,
                raw_data=data
            )
            
            return packet
            
        except Exception as e:
            _LOGGER.error(f"Failed to parse packet from bytes: {e}")
            return None

@dataclass
class TISDevice:
    """TIS Device Information"""
    device_id: str                          # Device address (e.g., "1.15")
    device_type: int                        # Device type code
    model_name: str = ""                    # Human readable model name
    firmware_version: str = ""              # Firmware version
    last_seen: Optional[datetime] = None    # Last communication timestamp
    online: bool = True                     # Device online status
    
    # Network information
    ip_address: Optional[str] = None        # IP address (for UDP devices)
    transport: str = "udp"                  # "udp" or "rs485"
    
    # Device capabilities and state
    capabilities: Dict[str, Any] = field(default_factory=dict)
    state: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    comment: str = ""                       # User comment/name
    room: str = ""                         # Room assignment
    tags: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.model_name:
            self.model_name = TIS_DEVICE_NAMES.get(self.device_type, f"Unknown Device")
        if self.last_seen is None:
            self.last_seen = datetime.now()
    
    @property
    def subnet(self) -> int:
        """Get subnet number"""
        try:
            return int(self.device_id.split('.')[0])
        except:
            return 0
    
    @property  
    def device_number(self) -> int:
        """Get device number"""
        try:
            return int(self.device_id.split('.')[1])
        except:
            return 0
    
    @property
    def device_type_name(self) -> str:
        """Get human readable device type name"""
        return TIS_DEVICE_NAMES.get(self.device_type, f"Unknown (0x{self.device_type:04X})")
    
    def update_last_seen(self):
        """Update last seen timestamp"""
        self.last_seen = datetime.now()
        self.online = True
    
    def update_state(self, key: str, value: Any):
        """Update device state"""
        self.state[key] = value
        self.update_last_seen()
    
    def get_state(self, key: str, default: Any = None) -> Any:
        """Get device state value"""
        return self.state.get(key, default)
    
    def has_capability(self, capability: str) -> bool:
        """Check if device has specific capability"""
        return capability in self.capabilities
    
    def get_supported_entities(self) -> List[str]:
        """Get list of supported Home Assistant entity types"""
        # Device type to entity mapping
        entity_map = {
            # Lighting devices
            0x0001: ["light"],               # Single Channel Lighting
            0x0258: ["light"],               # Dimmer 6CH
            0x0259: ["light"],               # Dimmer 4CH
            0x025A: ["light"],               # Dimmer 2CH
            
            # Climate control
            0x806C: ["climate", "sensor"],   # AC Control Panel
            0x0077: ["climate"],             # HVAC
            
            # Sensors
            0x8022: ["sensor"],              # Health Sensor
            0x0076: ["binary_sensor"],       # Digital Input
            0x0085: ["binary_sensor"],       # PIR Sensor
            
            # Switches
            0x0051: ["switch"],              # Universal Switch
            0x0052: ["switch"],              # Panel Control
            0x0053: ["switch"],              # Universal Switch Type 3
            0x0054: ["switch"],              # Universal Switch Type 4
            0x0056: ["switch"],              # Scene Switch
            
            # Security
            0x0030: ["alarm_control_panel", "binary_sensor"],  # Security Module
            0x0BE9: ["alarm_control_panel"],                   # Security SM
            
            # Curtains/Covers
            0x0041: ["cover"],               # Curtain Switch
        }
        
        return entity_map.get(self.device_type, [])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert device to dictionary"""
        return {
            'device_id': self.device_id,
            'device_type': self.device_type,
            'device_type_name': self.device_type_name,
            'model_name': self.model_name,
            'firmware_version': self.firmware_version,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'online': self.online,
            'ip_address': self.ip_address,
            'transport': self.transport,
            'capabilities': self.capabilities,
            'state': self.state,
            'comment': self.comment,
            'room': self.room,
            'tags': self.tags,
            'supported_entities': self.get_supported_entities()
        }

# ================== PROTOCOL UTILITIES ==================

def calculate_crc(data: bytes) -> int:
    """Calculate TIS CRC checksum (C-style implementation)"""
    try:
        crc = 0
        for byte in data:
            dat = (crc >> 8) & 0xFF
            crc = (crc << 8) & 0xFFFF
            crc ^= CRC_TABLE[dat ^ byte]
        return crc
    except Exception as e:
        _LOGGER.error(f"CRC calculation error: {e}")
        return 0

def validate_crc(packet_data: bytes) -> bool:
    """Validate packet CRC checksum"""
    try:
        if len(packet_data) < 2:
            return False
            
        # Extract CRC from packet (last 2 bytes)
        received_crc = (packet_data[-2] << 8) | packet_data[-1]
        
        # Calculate CRC for data without CRC bytes
        calculated_crc = calculate_crc(packet_data[:-2])
        
        return received_crc == calculated_crc
        
    except Exception as e:
        _LOGGER.error(f"CRC validation error: {e}")
        return False

def build_tis_packet(
    op_code: int,
    source_device: List[int] = None,
    target_device: List[int] = None,
    device_type: int = 0xFFFE,
    additional_data: bytes = b'',
    ip_address: str = "192.168.1.100"
) -> TISPacket:
    """Build TIS packet with proper defaults"""
    
    if source_device is None:
        source_device = [0x01, 0xFE]
    if target_device is None:
        target_device = [0xFF, 0xFF]
    
    packet = TISPacket(
        ip_address=ip_address,
        source_device_id=source_device,
        target_device_id=target_device,
        device_type=device_type,
        op_code=op_code,
        additional_data=additional_data
    )
    
    return packet

def create_discovery_packet(ip_address: str = "192.168.1.100") -> TISPacket:
    """Create discovery broadcast packet"""
    return build_tis_packet(
        op_code=TISOpCode.DISCOVERY_REQUEST.value,
        source_device=[0x01, 0xFE],
        target_device=[0xFF, 0xFF],  # Broadcast
        ip_address=ip_address
    )

def create_device_info_request(device_id: str, ip_address: str = "192.168.1.100") -> TISPacket:
    """Create device info request packet"""
    try:
        subnet, device = device_id.split('.')
        target_device = [int(subnet), int(device)]
    except:
        target_device = [0xFF, 0xFF]
    
    return build_tis_packet(
        op_code=TISOpCode.DEVICE_INFO_REQUEST.value,
        target_device=target_device,
        ip_address=ip_address
    )

def create_ac_control_packet(
    device_id: str,
    power_state: bool = True,
    temperature: int = 24,
    mode: int = 0,  # 0=Cool, 1=Heat, 2=Auto
    fan_speed: int = 1,  # 0=Auto, 1=Low, 2=Med, 3=High
    ip_address: str = "192.168.1.100"
) -> TISPacket:
    """Create AC control packet"""
    try:
        subnet, device = device_id.split('.')
        target_device = [int(subnet), int(device)]
    except:
        target_device = [0xFF, 0xFF]
    
    # AC control data format (from analysis)
    control_data = bytes([
        0x01 if power_state else 0x00,  # Power state
        mode & 0xFF,                     # HVAC mode
        temperature & 0xFF,              # Temperature
        0xFF,                            # Current temp (not set)
        fan_speed & 0xFF,               # Fan speed
    ])
    
    return build_tis_packet(
        op_code=TISOpCode.AC_CONTROL.value,
        target_device=target_device,
        device_type=TISDeviceType.TIS_MER_AC4G_PB.value,
        additional_data=control_data,
        ip_address=ip_address
    )

def create_light_control_packet(
    device_id: str,
    channel: int = 1,
    brightness: int = 100,  # 0-100%
    on_time_minutes: int = 0,
    on_time_seconds: int = 0,
    ip_address: str = "192.168.1.100"
) -> TISPacket:
    """Create light control packet"""
    try:
        subnet, device = device_id.split('.')
        target_device = [int(subnet), int(device)]
    except:
        target_device = [0xFF, 0xFF]
    
    # Light control data format (from analysis)
    control_data = bytes([
        channel & 0xFF,           # Channel number
        brightness & 0xFF,        # Brightness (0-100%)
        on_time_minutes & 0xFF,   # Runtime minutes
        on_time_seconds & 0xFF,   # Runtime seconds
    ])
    
    return build_tis_packet(
        op_code=TISOpCode.DEVICE_INFO_REQUEST.value,  # Use generic device control
        target_device=target_device,
        device_type=TISDeviceType.SINGLE_CHANNEL_LIGHTING.value,
        additional_data=control_data,
        ip_address=ip_address
    )

# ================== RESPONSE HANDLING ==================

@dataclass 
class TISCommandResponse:
    """TIS Command Response"""
    success: bool = False
    packet: Optional[TISPacket] = None
    error_message: str = ""
    response_time_ms: float = 0.0
    
    @property
    def data(self) -> bytes:
        """Get response data"""
        if self.packet:
            return self.packet.additional_data
        return b''

# Callback type for packet handlers
PacketHandler = Callable[[TISPacket], None]

# ================== DEVICE DISCOVERY ==================

class TISDeviceRegistry:
    """Registry for discovered TIS devices"""
    
    def __init__(self):
        self._devices: Dict[str, TISDevice] = {}
        self._packet_handlers: List[PacketHandler] = []
    
    def add_device(self, device: TISDevice) -> None:
        """Add or update device in registry"""
        self._devices[device.device_id] = device
        _LOGGER.info(f"Device registered: {device.device_id} - {device.model_name}")
    
    def get_device(self, device_id: str) -> Optional[TISDevice]:
        """Get device by ID"""
        return self._devices.get(device_id)
    
    def get_all_devices(self) -> List[TISDevice]:
        """Get all registered devices"""
        return list(self._devices.values())
    
    def get_devices_by_type(self, device_type: int) -> List[TISDevice]:
        """Get devices of specific type"""
        return [dev for dev in self._devices.values() if dev.device_type == device_type]
    
    def remove_device(self, device_id: str) -> bool:
        """Remove device from registry"""
        if device_id in self._devices:
            del self._devices[device_id]
            _LOGGER.info(f"Device removed: {device_id}")
            return True
        return False
    
    def update_device_state(self, device_id: str, state_data: Dict[str, Any]) -> bool:
        """Update device state"""
        device = self.get_device(device_id)
        if device:
            for key, value in state_data.items():
                device.update_state(key, value)
            return True
        return False
    
    def add_packet_handler(self, handler: PacketHandler) -> None:
        """Add packet handler"""
        self._packet_handlers.append(handler)
    
    def handle_packet(self, packet: TISPacket) -> None:
        """Process incoming packet"""
        try:
            # Update device registry based on packet
            self._update_from_packet(packet)
            
            # Notify handlers
            for handler in self._packet_handlers:
                try:
                    handler(packet)
                except Exception as e:
                    _LOGGER.error(f"Packet handler error: {e}")
                    
        except Exception as e:
            _LOGGER.error(f"Packet handling error: {e}")
    
    def _update_from_packet(self, packet: TISPacket) -> None:
        """Update device registry from received packet"""
        device_id = packet.source_address
        
        if device_id and device_id != "0.0":
            device = self.get_device(device_id)
            
            if device is None:
                # Create new device
                device = TISDevice(
                    device_id=device_id,
                    device_type=packet.device_type,
                    ip_address=packet.ip_address if packet.transport == "udp" else None,
                    transport=packet.transport
                )
                self.add_device(device)
            
            # Update device info
            device.update_last_seen()
            if packet.transport == "udp" and packet.ip_address:
                device.ip_address = packet.ip_address
                
            # Extract device info from discovery responses
            if packet.op_code == TISOpCode.DISCOVERY_RESPONSE.value:
                if packet.additional_data:
                    try:
                        # Try to extract device name from additional data
                        device_name = packet.additional_data.decode('ascii', errors='ignore').rstrip('\x00')
                        if device_name:
                            device.comment = device_name
                    except:
                        pass

# Global device registry instance
device_registry = TISDeviceRegistry()

# ================== EXPORTS ==================

__all__ = [
    # Enums
    'TISOpCode',
    'TISDeviceType', 
    
    # Data structures
    'TISPacket',
    'TISDevice',
    'TISCommandResponse',
    'TISDeviceRegistry',
    
    # Constants
    'TIS_DEVICE_NAMES',
    'CRC_TABLE',
    
    # Utility functions
    'calculate_crc',
    'validate_crc',
    'build_tis_packet',
    'create_discovery_packet',
    'create_device_info_request',
    'create_ac_control_packet',
    'create_light_control_packet',
    
    # Global instances
    'device_registry'
]

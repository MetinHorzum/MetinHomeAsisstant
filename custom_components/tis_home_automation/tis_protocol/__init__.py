"""
TIS Protocol Library
Complete implementation of TIS Home Automation protocol.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Any

from .core import *
from .helpers import *
from .communication import *

__version__ = "1.0.0"
__author__ = "TIS Protocol Reverse Engineering Team"

_LOGGER = logging.getLogger(__name__)

# Library configuration
class TISConfig:
    """TIS Protocol Library Configuration"""
    
    # Default values
    DEFAULT_UDP_PORT = 6000
    DEFAULT_RS485_BAUDRATE = 9600
    DEFAULT_TIMEOUT = 3.0
    DEFAULT_RETRY_COUNT = 3
    
    # Network configuration
    UDP_ENABLED = True
    RS485_ENABLED = False
    
    # Device discovery
    DISCOVERY_TIMEOUT = 30.0
    DISCOVERY_RETRIES = 3
    
    # Packet handling
    MAX_PACKET_SIZE = 1024
    CRC_VALIDATION = True
    
    @classmethod
    def configure_logging(cls, level: int = logging.INFO):
        """Configure logging for TIS protocol"""
        logging.getLogger(__name__).setLevel(level)
        _LOGGER.info(f"TIS Protocol Library v{__version__} initialized")

# Initialize logging
TISConfig.configure_logging()

__all__ = [
    # ===== CORE EXPORTS =====
    'TISOpCode',
    'TISDeviceType',
    'TISPacket',
    'TISDevice',
    'TISCommandResponse',
    'TISDeviceRegistry',
    'TIS_DEVICE_NAMES',
    'calculate_crc',
    'validate_crc',
    'build_tis_packet',
    'create_discovery_packet',
    'create_device_info_request',
    'create_ac_control_packet',
    'create_light_control_packet',
    'device_registry',
    
    # ===== HELPER EXPORTS =====
    # Byte manipulation
    'bytes_divmod',
    'bytes2hex',
    'hex_to_bytes',
    'hexstr',
    
    # CRC functions (verified)
    'packCRC',
    'checkCRC',
    'pack_crc_c_style',
    
    # Packet functions (verified)
    'build_packet',
    'parse_smartcloud_packet',
    
    # Utility functions
    'decode_mac',
    'int_to_8_bit_binary',
    'interpret_additional_data_by_opcode',
    'validate_packet_structure',
    
    # Constants
    'CRC_TAB',
    
    # ===== COMMUNICATION EXPORTS =====
    # Exception classes
    'TISCommunicationError',
    'TISTimeoutError',
    'TISConnectionError',
    
    # Transport classes
    'TISTransport',
    'TISUDPTransport',
    'TISRS485Transport',
    
    # Manager class
    'TISCommunicationManager',
    
    # Utility functions
    'get_available_serial_ports',
    'get_local_ip',
    'create_communication_manager',
    
    # Communication constants
    'DEFAULT_UDP_PORT',
    'DEFAULT_TIMEOUT',
    'DEFAULT_RETRY_COUNT',
    'DEFAULT_DISCOVERY_TIMEOUT',
    'BROADCAST_IP',
    'DISCOVERY_OPCODE',
    'DISCOVERY_RESPONSE_OPCODE',
    
    # ===== CONFIGURATION =====
    'TISConfig',
    '__version__',
    '__author__'
]
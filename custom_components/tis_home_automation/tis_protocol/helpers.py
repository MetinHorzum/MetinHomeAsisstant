"""
TIS Protocol Helper Functions
Core packet building and parsing functions from reverse engineering.
"""
from __future__ import annotations

import binascii
import logging
import struct
from ctypes import c_ushort, c_ubyte
from typing import Dict, List, Optional, Union, Any

_LOGGER = logging.getLogger(__name__)

# CRC Lookup Table (verified from TIS documentation)
CRC_TAB = [
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

# ================== BYTE MANIPULATION ==================

def bytes_divmod(int_param: int) -> tuple[int, int]:
    """Split integer into high and low bytes"""
    return divmod(int_param, 0x100)

def bytes2hex(data: bytes, rtype=None) -> Union[List[int], str]:
    """Convert bytes to hex representation
    
    Args:
        data: bytes array
        rtype: list for int list return, otherwise hex string
        
    Returns:
        List of ints or hex string
    """
    try:
        hex_string = binascii.hexlify(data).decode()
        hex_list = [int(hex_string[i:i+2], 16) for i in range(0, len(hex_string), 2)]
        
        if isinstance(rtype, list):
            return hex_list
        else:
            return hex_string
            
    except Exception as e:
        _LOGGER.error(f"bytes2hex conversion error: {e}")
        return [] if isinstance(rtype, list) else ""

def hex_to_bytes(hex_string: str) -> bytes:
    """Convert hex string to bytes"""
    try:
        hex_string = hex_string.replace(" ", "").replace(",", "").replace("0x", "")
        if len(hex_string) % 2 != 0:
            hex_string = "0" + hex_string
        return bytes.fromhex(hex_string)
    except Exception as e:
        _LOGGER.error(f"hex_to_bytes conversion error: {e}")
        return b''

def hexstr(data: bytes) -> str:
    """Convert bytes to hex string with spaces"""
    return " ".join(f"{x:02X}" for x in data)

# ================== CRC FUNCTIONS (VERIFIED) ==================

def packCRC(ptr: List[int]) -> List[int]:
    """Add CRC to packet (verified from TIS documentation)
    
    This is the exact C-style implementation from TIS documentation
    that was verified with real packets.
    """
    try:
        crc = c_ushort(0)
        
        # Process data starting from index 16 (after IP + header + separator)
        for i in range(len(ptr) - 16):
            data = c_ubyte(crc.value >> 8)
            crc.value <<= 8
            reg = c_ubyte(data.value ^ ptr[i + 16])
            crc = c_ushort(crc.value ^ CRC_TAB[reg.value])
        
        # Split CRC into high and low bytes
        crc_value_h, crc_value_l = bytes_divmod(crc.value)
        ptr.append(crc_value_h)
        ptr.append(crc_value_l)
        
        return ptr
        
    except Exception as e:
        _LOGGER.error(f"packCRC error: {e}")
        return ptr

def checkCRC(ptr: List[int]) -> bool:
    """Validate packet CRC (verified implementation)"""
    try:
        if len(ptr) < 2:
            return False
            
        # Extract CRC from end of packet
        crc_value_l = ptr.pop()
        crc_value_h = ptr.pop()
        
        # Calculate CRC for packet without CRC bytes
        targ_ptr = packCRC(ptr.copy())  # Use copy to not modify original
        
        # Compare calculated vs received CRC
        return (targ_ptr[len(targ_ptr) - 1] == crc_value_l and
                targ_ptr[len(targ_ptr) - 2] == crc_value_h)
                
    except Exception as e:
        _LOGGER.error(f"checkCRC error: {e}")
        return False

def pack_crc_c_style(data: List[int]) -> int:
    """
    TIS C-style CRC calculation (VERIFIED with real packets)
    
    This is the exact Pack_crc C function from TIS documentation:
    void Pack_crc(unchar *ptr, unchar len)
    {
        unint crc;
        unchar dat;
        crc=0;
        while(len--!=0)
        {
            dat=crc>>8;
            crc<<=8;
            crc^=CRC_TAB[dat^*ptr];
            ptr++;
        }
        *ptr=crc>>8;
        ptr++;
        *ptr=crc;
    }
    """
    try:
        crc = 0  # unint crc; crc=0;
        
        # while(len--!=0) - Python equivalent
        for byte in data:
            dat = (crc >> 8) & 0xFF  # dat=crc>>8; - high byte
            crc = (crc << 8) & 0xFFFF  # crc<<=8; - shift left, keep 16-bit
            crc ^= CRC_TAB[dat ^ byte]  # crc^=CRC_TAB[dat^*ptr];
            # ptr++; - handled by for loop
        
        return crc
        
    except Exception as e:
        _LOGGER.error(f"pack_crc_c_style error: {e}")
        return 0

# ================== PACKET BUILDING (VERIFIED) ==================

def build_packet(
    operation_code: List[int],
    ip_address: str,
    destination_mac: str = "AA:AA:AA:AA:AA:AA:AA:AA",
    source_mac: str = "CB:CB:CB:CB:CB:CB:CB:CB", 
    device_id: List[int] = None,
    source_device_id: List[int] = None,
    device_type: List[int] = None,
    additional_packets: List[int] = None,
    header: str = "SMARTCLOUD"
) -> List[int]:
    """
    Build TIS SMARTCLOUD packet (VERIFIED implementation)
    
    This function builds packets in the exact format verified
    with real TIS devices and protocol analysis.
    
    Args:
        operation_code: Op code [high_byte, low_byte]  
        ip_address: Source IP address "192.168.1.100"
        device_id: Target device ID [high_byte, low_byte]
        source_device_id: Source device ID [high_byte, low_byte]
        device_type: Device Type [high_byte, low_byte] (default: 0xFFFE)
        additional_packets: Additional data bytes list
        header: Packet header (default: SMARTCLOUD)
        
    Returns:
        Complete packet (IP + SMARTCLOUD + data + CRC) byte list
    """
    try:
        # Set defaults
        if device_id is None:
            device_id = []
        if source_device_id is None:
            source_device_id = [0x01, 0xFE]
        if device_type is None:
            device_type = [0xFF, 0xFE]
        if additional_packets is None:
            additional_packets = []
        
        # Convert IP address to bytes
        ip_bytes = [int(part) for part in ip_address.split(".")]
        
        # Convert header to bytes
        header_bytes = [ord(char) for char in header]
        
        # Calculate length (source_device_id + device_type + operation_code + device_id + additional)
        length = 11 + len(additional_packets)
        
        # Build packet structure:
        # IP(4) + HEADER(10) + SEPARATOR(2) + LENGTH(1) + SOURCE_DEV(2) + DEV_TYPE(2) + OP_CODE(2) + TARGET_DEV(2) + ADDITIONAL + CRC(2)
        packet = (
            ip_bytes +                    # IP address (4 bytes)
            header_bytes +                # SMARTCLOUD header (10 bytes)  
            [0xAA, 0xAA] +               # Separator (2 bytes)
            [length] +                    # Length (1 byte)
            source_device_id +            # Source device (2 bytes)
            device_type +                 # Device type (2 bytes)
            operation_code +              # Operation code (2 bytes)
            device_id +                   # Target device (2 bytes)
            additional_packets            # Additional data (variable)
        )
        
        # Add CRC using verified function
        packet = packCRC(packet)
        
        return packet
        
    except Exception as e:
        _LOGGER.error(f"build_packet error: {e}")
        return []

# ================== PACKET PARSING (VERIFIED) ==================

def parse_smartcloud_packet(packet_data: bytes) -> Dict[str, Any]:
    """
    Parse SMARTCLOUD format packet (VERIFIED implementation)
    
    This parser was verified against real TIS packets and 
    successfully extracts all packet components.
    
    Args:
        packet_data: Raw packet data
        
    Returns:
        dict: Parsed packet information with validation status
    """
    try:
        if len(packet_data) < 29:  # Minimum packet size
            return {'valid': False, 'error': 'Packet too short'}
        
        # IP address (4 bytes)
        ip = ".".join(str(b) for b in packet_data[0:4])
        
        # Header (10 bytes - "SMARTCLOUD")
        header = packet_data[4:14].decode('ascii', errors='ignore')
        
        # Separator check (2 bytes - 0xAA 0xAA)
        if packet_data[14] != 0xAA or packet_data[15] != 0xAA:
            return {'valid': False, 'error': 'SMARTCLOUD separator not found'}
        
        # Length (1 byte)  
        length = packet_data[16]
        
        # Validate packet length
        if len(packet_data) < 17 + length + 2:  # 17 (header) + length + 2 (CRC)
            return {'valid': False, 'error': 'Packet length mismatch'}
        
        # Source device (2 bytes)
        source_device = [packet_data[17], packet_data[18]]
        
        # Device type (2 bytes)
        device_type = (packet_data[19] << 8) | packet_data[20]
        
        # Operation code (2 bytes)
        op_code = (packet_data[21] << 8) | packet_data[22]
        
        # Target device (2 bytes) 
        target_device = [packet_data[23], packet_data[24]]
        
        # Additional data (length - 11 bytes)
        additional_data_length = length - 11
        additional_data = b''
        if additional_data_length > 0:
            additional_data = packet_data[25:25 + additional_data_length]
        
        # CRC (2 bytes)
        crc_offset = 25 + additional_data_length
        if len(packet_data) < crc_offset + 2:
            return {'valid': False, 'error': 'CRC not found'}
        
        crc = (packet_data[crc_offset] << 8) | packet_data[crc_offset + 1]
        
        # CRC validation using verified function
        packet_for_crc = list(packet_data[:crc_offset + 2])
        crc_valid = checkCRC(packet_for_crc.copy())  # Use copy to avoid modification
        
        return {
            'valid': True,
            'ip': ip,
            'header': header,
            'length': length,
            'source_device': source_device,
            'device_type': device_type,
            'op_code': op_code,
            'target_device': target_device,
            'additional_data': additional_data,
            'crc': crc,
            'crc_valid': crc_valid,
            'raw_data': packet_data
        }
        
    except Exception as e:
        _LOGGER.error(f"parse_smartcloud_packet error: {e}")
        return {'valid': False, 'error': str(e)}

# ================== UTILITY FUNCTIONS ==================

def decode_mac(mac: List[int]) -> str:
    """Convert MAC address from byte list to string"""
    try:
        return ":".join([f"{byte:02X}" for byte in mac])
    except Exception as e:
        _LOGGER.error(f"decode_mac error: {e}")
        return "00:00:00:00:00:00"

def int_to_8_bit_binary(number: int) -> str:
    """Convert integer to 8-bit binary string (reversed)"""
    try:
        binary_string = bin(number)[2:]
        return binary_string.zfill(8)[::-1]
    except Exception as e:
        _LOGGER.error(f"int_to_8_bit_binary error: {e}")
        return "00000000"

# ================== PACKET INTERPRETATION ==================

def interpret_additional_data_by_opcode(op_code: int, data: bytes) -> str:
    """Interpret additional data based on OpCode (from protocol analysis)"""
    try:
        if len(data) == 0:
            return ""
        
        result = []
        
        # Firmware Version Response (0xEFFE)
        if op_code == 0xEFFE:
            try:
                text = data.decode('ascii', errors='ignore').rstrip('\x00')
                if text:
                    result.append(f"📌 Firmware: {text}")
            except:
                pass
        
        # Device Name/Discovery Response (0x000F)
        elif op_code == 0x000F:
            try:
                text = data.decode('ascii', errors='ignore').rstrip('\x00')
                if text:
                    result.append(f"📌 Device Name: {text}")
            except:
                pass
        
        # MAC/Unique ID Response (0xF004)
        elif op_code == 0xF004:
            if len(data) >= 8:
                # First 8 bytes might be MAC/ID
                mac_like = ':'.join(f'{b:02X}' for b in data[:8])
                result.append(f"📌 Unique ID/MAC: {mac_like}")
        
        # Channel/Sensor Response (0x2025) - Health Sensor
        elif op_code == 0x2025:
            if len(data) >= 14:
                lux = (data[5] << 8) | data[6] if len(data) > 6 else 0
                noise = (data[7] << 8) | data[8] if len(data) > 8 else 0
                eco2 = (data[9] << 8) | data[10] if len(data) > 10 else 0
                tvoc = (data[11] << 8) | data[12] if len(data) > 12 else 0
                temp = data[13] if len(data) > 13 else 0
                hum = data[14] if len(data) > 14 else 0
                
                result.append(f"📌 Health Sensor Data:")
                result.append(f"   LUX: {lux}, Noise: {noise}dB")
                result.append(f"   eCO2: {eco2}ppm, TVOC: {tvoc}ppb")
                result.append(f"   Temp: {temp}°C, Hum: {hum}%")
        
        # Status Response (0x0281)
        elif op_code == 0x0281:
            if len(data) >= 1:
                status = data[0]
                status_names = {
                    0x00: "Off/Idle",
                    0x01: "On/Active", 
                    0x02: "Standby",
                    0xFF: "Error"
                }
                result.append(f"📌 Status: {status_names.get(status, f'0x{status:02X}')}")
        
        # AC Control/Status
        elif op_code in [0xE0ED, 0xE0EE, 0xE0EF]:
            if len(data) >= 4:
                power = data[0] if len(data) > 0 else 0
                mode = data[1] if len(data) > 1 else 0
                temp = data[2] if len(data) > 2 else 0
                fan = data[3] if len(data) > 3 else 0
                
                modes = ["Cool", "Heat", "Fan", "Auto"]
                fans = ["Auto", "Low", "Medium", "High"]
                
                result.append(f"📌 AC Control:")
                result.append(f"   Power: {'ON' if power else 'OFF'}")
                result.append(f"   Mode: {modes[mode] if mode < 4 else f'Unknown({mode})'}")
                result.append(f"   Temp: {temp}°C")
                result.append(f"   Fan: {fans[fan] if fan < 4 else f'Unknown({fan})'}")
        
        return "\n   ".join(result) if result else ""
        
    except Exception as e:
        _LOGGER.error(f"interpret_additional_data_by_opcode error: {e}")
        return f"Parse error: {e}"

# ================== VALIDATION HELPERS ==================

def validate_packet_structure(packet_data: bytes) -> Dict[str, Any]:
    """Validate basic packet structure"""
    validation = {
        'valid': True,
        'errors': [],
        'warnings': []
    }
    
    try:
        # Minimum size check
        if len(packet_data) < 29:
            validation['valid'] = False
            validation['errors'].append("Packet too short (minimum 29 bytes)")
            return validation
        
        # Header check
        try:
            header = packet_data[4:14].decode('ascii', errors='strict')
            if header != "SMARTCLOUD":
                validation['warnings'].append(f"Non-standard header: {header}")
        except UnicodeDecodeError:
            validation['errors'].append("Invalid header encoding")
        
        # Separator check
        if packet_data[14] != 0xAA or packet_data[15] != 0xAA:
            validation['errors'].append("Missing SMARTCLOUD separator (0xAA 0xAA)")
        
        # Length validation
        length = packet_data[16]
        expected_size = 17 + length + 2  # Header(17) + data(length) + CRC(2)
        if len(packet_data) != expected_size:
            validation['errors'].append(f"Length mismatch: expected {expected_size}, got {len(packet_data)}")
        
        # CRC validation
        if validation['valid']:  # Only check CRC if basic structure is valid
            packet_copy = list(packet_data)
            if not checkCRC(packet_copy):
                validation['warnings'].append("CRC validation failed")
        
        if validation['errors']:
            validation['valid'] = False
            
    except Exception as e:
        validation['valid'] = False
        validation['errors'].append(f"Validation error: {e}")
    
    return validation

# ================== ALIASES FOR COMPATIBILITY ==================

# Add aliases for functions expected by other modules
build_tis_packet = build_packet
calculate_crc16 = pack_crc_c_style
get_ip_bytes = lambda ip: [int(part) for part in ip.split(".")]

# ================== EXPORTS ==================

__all__ = [
    # Byte manipulation
    'bytes_divmod',
    'bytes2hex',
    'hex_to_bytes',
    'hexstr',
    
    # CRC functions (verified)
    'packCRC',
    'checkCRC',
    'pack_crc_c_style',
    'calculate_crc16',
    
    # Packet functions (verified)
    'build_packet',
    'build_tis_packet',
    'parse_smartcloud_packet',
    
    # Utility functions
    'decode_mac',
    'int_to_8_bit_binary',
    'interpret_additional_data_by_opcode',
    'validate_packet_structure',
    'get_ip_bytes',
    
    # Constants
    'CRC_TAB'
]
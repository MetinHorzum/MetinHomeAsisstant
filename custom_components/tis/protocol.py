"""
TIS Protocol Helper - Sadeleştirilmiş TIS paket oluşturma ve CRC fonksiyonları
TISControlProtocol kütüphanesinden homeassistant bağımlılığı olmadan kopyalanmıştır.
"""

import binascii
from ctypes import *

# ================== CRC FONKSİYONLARI ==================

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
    0x6E17, 0x7E36, 0x4E55, 0x5E74, 0x2E93, 0x3EB2, 0x0ED1, 0x1EF0,
]


def bytes_divmod(intParam):
    """Integer'ı high ve low byte'lara böl"""
    return divmod(intParam, 0x100)


def packCRC(ptr):
    """Pakete CRC ekle"""
    crc = c_ushort(0)
    for i in range(len(ptr) - 16):
        data = c_ubyte(crc.value >> 8)
        crc.value <<= 8
        reg = c_ubyte(data.value ^ ptr[i + 16])
        crc = c_ushort(crc.value ^ CRC_TAB[reg.value])
    crcValueH, crcValueL = bytes_divmod(crc.value)
    ptr.append(crcValueH)
    ptr.append(crcValueL)
    return ptr


def checkCRC(ptr):
    """Paketin CRC'sini kontrol et"""
    crcValueL = ptr.pop()
    crcValueH = ptr.pop()
    targPtr = packCRC(ptr)
    if (targPtr[len(targPtr) - 1] == crcValueL) and (
        targPtr[len(targPtr) - 2] == crcValueH
    ):
        return True
    else:
        return False


# ================== BYTES HELPER FONKSİYONLARI ==================

def bytes2hex(data, rtype=[]):
    """Bytes'ı hex'e çevir
    
    Args:
        data: bytes array
        rtype: list ise int listesi döner, değilse hex string döner
        
    Returns:
        list of ints veya hex string
    """
    hex_string = binascii.hexlify(data).decode()
    hex_list = [int(hex_string[i : i + 2], 16) for i in range(0, len(hex_string), 2)]
    if isinstance(rtype, list):
        return hex_list
    else:
        return hex_string


# protocol.py
def build_packet(
    operation_code: list,
    ip_address: str,
    device_id: list = [],
    source_device_id: list = [0x01, 0xFE],
    device_type: list = [0xFF, 0xFE],
    additional_packets: list = [],
    header="SMARTCLOUD",
):
    """TIS SMARTCLOUD paketi oluştur (TIS_UDP_Tester.py ile uyumlu)"""
    # IP adresini byte'lara çevir
    ip_bytes = [int(part) for part in ip_address.split(".")]
    header_bytes = [ord(char) for char in header]
    
    # Uzunluk: source_id(2) + dev_type(2) + opcode(2) + target_id(2) + additional + separator(2) + length_byte(1)
    # Ancak TIS standardında length genelde 11 + additional_data uzunluğudur.
    length = 11 + len(additional_packets)
    
    packet = (
        ip_bytes
        + header_bytes
        + [0xAA, 0xAA]
        + [length]
        + source_device_id
        + device_type
        + operation_code
        + device_id
        + additional_packets
    )
    
    # Pakete CRC ekle
    from .protocol import packCRC
    packet = packCRC(packet)
    return packet

def decode_mac(mac: list):
    """MAC adresini byte listesinden string'e çevir"""
    return ":".join([f"{byte:02X}" for byte in mac])


def int_to_8_bit_binary(number):
    """Integer'ı 8-bit binary string'e çevir (ters çevrilmiş)"""
    binary_string = bin(number)[2:]
    return binary_string.zfill(8)[::-1]


# ================== PAKET PARSE FONKSİYONU ==================

def parse_smartcloud_packet(packet_data: bytes) -> dict:
    """SMARTCLOUD formatındaki paketi parse et
    
    Args:
        packet_data: Ham paket verisi
        
    Returns:
        dict: {
            'valid': bool,
            'ip': str,
            'header': str,
            'length': int,
            'source_device': list[int, int],
            'device_type': int,
            'op_code': int,
            'target_device': list[int, int],
            'additional_data': bytes,
            'crc': int,
            'crc_valid': bool
        }
    """
    try:
        if len(packet_data) < 29:  # Minimum paket boyutu
            return {'valid': False, 'error': 'Paket çok kısa'}
        
        # IP adresi (4 byte)
        ip = ".".join(str(b) for b in packet_data[0:4])
        
        # Header (10 byte - "SMARTCLOUD")
        header = packet_data[4:14].decode('ascii', errors='ignore')
        
        # 0xAA 0xAA separator (2 byte)
        if packet_data[14] != 0xAA or packet_data[15] != 0xAA:
            return {'valid': False, 'error': 'SMARTCLOUD separator bulunamadı'}
        
        # Length (1 byte)
        length = packet_data[16]
        
        # Source device (2 byte)
        source_device = [packet_data[17], packet_data[18]]
        
        # Device type (2 byte - 0xFFFE sabit)
        device_type = (packet_data[19] << 8) | packet_data[20]
        
        # Operation code (2 byte)
        op_code = (packet_data[21] << 8) | packet_data[22]
        
        # Target device (2 byte)
        target_device = [packet_data[23], packet_data[24]]
        
        # Additional data (length - 11 byte)
        additional_data_length = length - 11
        additional_data = packet_data[25:25 + additional_data_length]
        
        # CRC (2 byte)
        crc_offset = 25 + additional_data_length
        if len(packet_data) < crc_offset + 2:
            return {'valid': False, 'error': 'CRC bulunamadı'}
        
        crc = (packet_data[crc_offset] << 8) | packet_data[crc_offset + 1]
        
        # CRC doğrulama
        packet_for_crc = list(packet_data[:crc_offset + 2])
        crc_valid = checkCRC(packet_for_crc)
        
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
            'crc_valid': crc_valid
        }
        
    except Exception as e:
        return {'valid': False, 'error': str(e)}

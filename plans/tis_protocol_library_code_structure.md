# TIS Protocol Library - Kod Yapısı ve Implementation Planı

## 📂 Proje Klasör Yapısı

```
tis_protocol/
├── __init__.py                 # Ana kütüphane entry point
├── core.py                     # Temel veri yapıları ve protokol işlemleri
├── communication/
│   ├── __init__.py
│   ├── manager.py             # Ana iletişim yöneticisi
│   ├── rs485_handler.py       # RS485 seri iletişim
│   ├── udp_handler.py         # UDP network iletişim
│   └── transport.py           # Transport abstraction layer
├── discovery/
│   ├── __init__.py
│   ├── discovery.py           # Device discovery servisi
│   ├── device_mapper.py       # Device capability mapping
│   └── scanner.py             # Network/RS485 scanner
├── protocol/
│   ├── __init__.py
│   ├── parser.py              # Packet parsing
│   ├── builder.py             # Packet building
│   ├── opcodes.py             # OpCode tanımları
│   └── crc.py                 # CRC hesaplama
├── devices/
│   ├── __init__.py
│   ├── base.py                # Base device class
│   ├── lighting.py            # Lighting devices
│   ├── climate.py             # AC/HVAC devices
│   ├── sensors.py             # Sensor devices
│   └── switches.py            # Switch/relay devices
├── exceptions.py              # TIS specific exceptions
├── utils.py                   # Utility functions
└── constants.py               # Sabitler ve device mappings
```

## 🔧 Core Module (core.py)

### Temel Data Structures

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum

class TISTransport(Enum):
    """İletişim transport tipi"""
    RS485 = "rs485"
    UDP = "udp"

class TISCommand(Enum):
    """TIS komut tipleri - Analiz sonuçlarından"""
    DISCOVERY_REQUEST = 0x000E
    DISCOVERY_RESPONSE = 0x000F
    DEVICE_CONTROL = 0x0031
    DEVICE_STATUS = 0x0032
    AC_CONTROL = 0xE0EE
    AC_STATUS = 0xE0ED
    SENSOR_QUERY = 0x2024
    SENSOR_RESPONSE = 0x2025
    # ... diğer komutlar

@dataclass
class TISAddress:
    """TIS cihaz adresi (subnet.device format)"""
    subnet: int
    device: int
    
    def __str__(self) -> str:
        return f"{self.subnet}.{self.device}"
    
    @classmethod
    def from_string(cls, address_str: str) -> 'TISAddress':
        subnet, device = map(int, address_str.split('.'))
        return cls(subnet=subnet, device=device)

@dataclass
class TISPacket:
    """TIS protokol paketi - SMARTCLOUD format"""
    source_ip: Optional[str] = None
    header: str = "SMARTCLOUD"
    length: int = 0
    source_device: TISAddress = None
    device_type: int = 0xFFFE
    op_code: int = 0x0000
    target_device: TISAddress = None
    additional_data: bytes = b''
    crc: Optional[int] = None
    crc_valid: bool = False
    timestamp: datetime = field(default_factory=datetime.now)
    transport: TISTransport = TISTransport.UDP
    
    def to_bytes(self) -> bytes:
        """Paketi byte array'e çevir"""
        # Implementation details...
    
    @staticmethod
    def calculate_crc(data: bytes) -> int:
        """TIS CRC algoritması"""
        # CRC_TABLE tablosu kullanarak hesaplama...

@dataclass
class TISDevice:
    """TIS cihaz bilgileri"""
    device_id: str  # "1.68" format
    address: TISAddress
    device_type: int = 0x0000
    model_name: str = "Unknown"
    ip_address: Optional[str] = None
    firmware_version: Optional[str] = None
    online: bool = False
    last_seen: datetime = field(default_factory=datetime.now)
    supported_entities: List[str] = field(default_factory=list)
    channels: int = 1
    features: Dict[str, Any] = field(default_factory=dict)
```

## 📡 Communication Manager (communication/manager.py)

### Ana İletişim Sınıfı

```python
import asyncio
from typing import Optional, Dict, List
from ..core import TISPacket, TISDevice, TISResponse, TISAddress

class TISCommunicationManager:
    """Ana iletişim yöneticisi - hem RS485 hem UDP destekler"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.rs485_handler = None
        self.udp_handler = None
        self.active_connections = {}
        self.response_handlers = {}
        self._command_queue = asyncio.Queue()
        self._monitoring = False
        
    async def initialize(self) -> bool:
        """İletişim katmanını başlat"""
        try:
            # UDP handler başlat
            if self.config.get('udp_enabled', True):
                from .udp_handler import TISUDPHandler
                self.udp_handler = TISUDPHandler(
                    interface=self.config.get('udp_interface', '0.0.0.0'),
                    port=self.config.get('udp_port', 6000)
                )
                await self.udp_handler.start_listening()
                
            # RS485 handler başlat
            if self.config.get('rs485_enabled', False):
                from .rs485_handler import TISRS485Handler
                self.rs485_handler = TISRS485Handler(
                    port=self.config.get('rs485_port', '/dev/ttyUSB0'),
                    baudrate=self.config.get('rs485_baudrate', 9600)
                )
                await self.rs485_handler.connect()
                
            return True
        except Exception as e:
            logger.error(f"Communication initialization failed: {e}")
            return False
    
    async def send_command(self, 
                          device_id: str, 
                          op_code: int, 
                          data: bytes = b'',
                          timeout: float = 5.0) -> TISResponse:
        """Cihaza komut gönder"""
        try:
            device = await self.get_device(device_id)
            if not device:
                return TISResponse(
                    success=False,
                    op_code=op_code,
                    error_message=f"Device {device_id} not found"
                )
            
            # Packet oluştur
            packet = TISPacket(
                op_code=op_code,
                source_device=TISAddress(1, 254),  # Gateway address
                target_device=device.address,
                device_type=device.device_type,
                additional_data=data,
                transport=device.transport
            )
            
            # Uygun transport ile gönder
            if device.transport == TISTransport.UDP and self.udp_handler:
                return await self.udp_handler.send_command(packet, timeout)
            elif device.transport == TISTransport.RS485 and self.rs485_handler:
                return await self.rs485_handler.send_command(packet, timeout)
            else:
                return TISResponse(
                    success=False,
                    op_code=op_code,
                    error_message="No suitable transport available"
                )
                
        except Exception as e:
            return TISResponse(
                success=False,
                op_code=op_code,
                error_message=str(e)
            )
    
    async def discover_devices(self, timeout: int = 30) -> List[TISDevice]:
        """Ağdaki TIS cihazlarını keşfet"""
        from ..discovery.discovery import TISDeviceDiscovery
        
        discovery = TISDeviceDiscovery(self)
        devices = await discovery.scan_network(timeout)
        
        # Device'ları cache'le
        for device in devices:
            self.active_connections[device.device_id] = device
            
        return devices
    
    async def start_monitoring(self) -> None:
        """Cihaz durumu izlemeyi başlat"""
        self._monitoring = True
        
        # UDP monitoring
        if self.udp_handler:
            asyncio.create_task(self._monitor_udp())
            
        # RS485 monitoring  
        if self.rs485_handler:
            asyncio.create_task(self._monitor_rs485())
    
    async def stop_monitoring(self) -> None:
        """İzlemeyi durdur"""
        self._monitoring = False
```

## 🔍 Device Discovery (discovery/discovery.py)

### Discovery Servisi

```python
from ..core import TISDevice, TISPacket, TISCommand, TISAddress
from .device_mapper import DeviceCapabilityMapper

class TISDeviceDiscovery:
    """Otomatik cihaz keşif servisi"""
    
    def __init__(self, communication_manager):
        self.comm_manager = communication_manager
        self.device_mapper = DeviceCapabilityMapper()
        self.discovered_devices = {}
        
    async def scan_network(self, timeout: int = 30) -> List[TISDevice]:
        """Ağ tarama - hem UDP hem RS485"""
        devices = []
        
        # UDP broadcast discovery
        if self.comm_manager.udp_handler:
            udp_devices = await self._scan_udp_network(timeout // 2)
            devices.extend(udp_devices)
            
        # RS485 sequential scan
        if self.comm_manager.rs485_handler:
            rs485_devices = await self._scan_rs485_network(timeout // 2)
            devices.extend(rs485_devices)
            
        # Device capability mapping
        for device in devices:
            capabilities = await self.device_mapper.get_capabilities(device.device_type)
            device.supported_entities = capabilities.supported_entities
            device.features = capabilities.features
            
        return devices
    
    async def _scan_udp_network(self, timeout: int) -> List[TISDevice]:
        """UDP broadcast ile discovery"""
        devices = []
        
        # Discovery request paketi oluştur
        discovery_packet = TISPacket(
            op_code=TISCommand.DISCOVERY_REQUEST.value,
            source_device=TISAddress(1, 254),  # Gateway
            target_device=TISAddress(255, 255),  # Broadcast
            transport=TISTransport.UDP
        )
        
        # Broadcast gönder
        await self.comm_manager.udp_handler.send_broadcast(discovery_packet.to_bytes())
        
        # Response'ları bekle
        start_time = time.time()
        while time.time() - start_time < timeout:
            responses = await self.comm_manager.udp_handler.get_responses(1.0)
            for response in responses:
                device = await self._process_discovery_response(response)
                if device:
                    devices.append(device)
                    
        return devices
    
    async def _process_discovery_response(self, packet: TISPacket) -> Optional[TISDevice]:
        """Discovery response'unu işle"""
        if packet.op_code != TISCommand.DISCOVERY_RESPONSE.value:
            return None
            
        device = TISDevice(
            device_id=str(packet.source_device),
            address=packet.source_device,
            device_type=packet.device_type,
            ip_address=packet.source_ip,
            transport=packet.transport,
            online=True
        )
        
        # Device name extract
        if packet.additional_data:
            device_name = packet.additional_data.decode('utf-8', errors='ignore').rstrip('\x00')
            device.model_name = device_name
            
        # Additional device info query
        await self._query_device_details(device)
        
        return device
    
    async def _query_device_details(self, device: TISDevice) -> None:
        """Cihaz detaylarını sorgula"""
        # Firmware version query
        try:
            firmware_response = await self.comm_manager.send_command(
                device.device_id,
                TISCommand.FIRMWARE_QUERY.value,
                timeout=2.0
            )
            if firmware_response.success:
                device.firmware_version = firmware_response.data.decode('ascii', errors='ignore').strip()
        except:
            pass
            
        # MAC address query
        try:
            mac_response = await self.comm_manager.send_command(
                device.device_id,
                TISCommand.MAC_QUERY.value,
                timeout=2.0
            )
            if mac_response.success and len(mac_response.data) >= 6:
                mac_bytes = mac_response.data[:6]
                device.mac_address = ":".join(f"{b:02X}" for b in mac_bytes)
        except:
            pass
```

## 🏠 Device Capability Mapping (discovery/device_mapper.py)

### Cihaz Yetenek Eşleme Sistemi

```python
from dataclasses import dataclass
from typing import Dict, List, Any

@dataclass
class TISDeviceCapabilities:
    device_type: int
    model_name: str
    supported_entities: List[str]  # ["switch", "light", "sensor"]
    channels: int
    features: Dict[str, Any]
    opcodes: Dict[str, int]  # Feature -> OpCode mapping

class DeviceCapabilityMapper:
    """Cihaz tiplerini Home Assistant entity'lerine eşler"""
    
    # Analiz edilen cihaz mappings (rs485_tis_gui_tester.py'den alınan)
    DEVICE_MAPPINGS = {
        # Lighting Devices
        0x0001: {  # Single Channel Lighting
            "model_name": "Single Channel Lighting",
            "entities": ["light"],
            "channels": 1,
            "features": {
                "brightness": True,
                "on_off": True,
                "dimmer": True
            },
            "opcodes": {
                "control": 0x0031,
                "status": 0x0032,
                "update": 0x0033
            }
        },
        
        # AC Control - Öncelikli cihaz
        0x806C: {  # TIS-MER-AC4G-PB
            "model_name": "TIS-MER-AC4G-PB",
            "entities": ["climate", "sensor"],
            "channels": 4,
            "features": {
                "temperature": True,
                "target_temperature": True,
                "hvac_modes": ["cool", "heat", "auto", "off"],
                "fan_modes": ["auto", "low", "medium", "high"],
                "current_temperature": True
            },
            "opcodes": {
                "ac_control": 0xA12E,
                "ac_status": 0xA12F,
                "temp_query": 0xE0F8,
                "ac_name_query": 0xA13C
            }
        },
        
        # Health Sensors - Öncelikli
        0x8022: {  # TIS-HEALTH-CM
            "model_name": "TIS Health Sensor",
            "entities": ["sensor"],
            "channels": 1,
            "features": {
                "temperature": True,
                "humidity": True,
                "co2": True,
                "tvoc": True,
                "noise": True,
                "lux": True
            },
            "opcodes": {
                "sensor_query": 0x2024,
                "sensor_response": 0x2025
            }
        },
        
        # Digital Input - Test ortamında var
        0x0076: {  # TIS-4DI-IN
            "model_name": "TIS 4 Zone Digital Input",
            "entities": ["binary_sensor"],
            "channels": 4,
            "features": {
                "contact_sensor": True,
                "motion_detection": True,
                "door_window": True
            },
            "opcodes": {
                "input_query": 0x012C,
                "status_query": 0xD205
            }
        },
        
        # Universal Switches
        0x0051: {  # Universal Switch Type 1
            "model_name": "Universal Switch Type 1",
            "entities": ["switch"],
            "channels": 1,
            "features": {
                "on_off": True,
                "room_control": True
            },
            "opcodes": {
                "control": 0x0031,
                "status": 0x0032
            }
        },
        
        # Dimmer Controllers
        0x0258: {  # DIM-6CH-2A
            "model_name": "Dimmer 6CH 2A",
            "entities": ["light"],
            "channels": 6,
            "features": {
                "brightness": True,
                "on_off": True,
                "dimmer": True
            },
            "opcodes": {
                "control": 0x0031,
                "status": 0x0032
            }
        },
        
        # Scene Controllers
        0x0056: {  # Scene Switch
            "model_name": "Scene Control Switch",
            "entities": ["switch", "scene"],
            "channels": 8,
            "features": {
                "scene_control": True,
                "multiple_scenes": True
            },
            "opcodes": {
                "scene_execute": 0x80A1,
                "scene_store": 0x80A2
            }
        }
    }
    
    async def get_capabilities(self, device_type: int) -> TISDeviceCapabilities:
        """Device type'tan capability döndür"""
        mapping = self.DEVICE_MAPPINGS.get(device_type, {
            "model_name": f"Unknown (0x{device_type:04X})",
            "entities": ["sensor"],  # Fallback
            "channels": 1,
            "features": {},
            "opcodes": {"status": 0x0032}
        })
        
        return TISDeviceCapabilities(
            device_type=device_type,
            model_name=mapping["model_name"],
            supported_entities=mapping["entities"],
            channels=mapping["channels"],
            features=mapping["features"],
            opcodes=mapping["opcodes"]
        )
```

## 🔌 Transport Handlers

### UDP Handler (communication/udp_handler.py)

```python
import asyncio
import socket
from typing import Optional, List
from ..core import TISPacket, TISResponse

class TISUDPHandler:
    """UDP network iletişim yöneticisi"""
    
    def __init__(self, interface: str = "0.0.0.0", port: int = 6000):
        self.interface = interface
        self.port = port
        self.socket = None
        self.read_task = None
        self.response_queue = asyncio.Queue()
        
    async def start_listening(self) -> bool:
        """UDP dinlemeyi başlat"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.socket.bind((self.interface, self.port))
            self.socket.setblocking(False)
            
            # Async reading task
            self.read_task = asyncio.create_task(self._read_packets())
            return True
        except Exception as e:
            logger.error(f"UDP listener start failed: {e}")
            return False
    
    async def send_command(self, packet: TISPacket, timeout: float = 5.0) -> TISResponse:
        """UDP komut gönder ve response bekle"""
        try:
            # Paketi gönder
            data = packet.to_bytes()
            target_ip = packet.target_device.subnet == 255 and "255.255.255.255" or packet.source_ip
            
            self.socket.sendto(data, (target_ip, self.port))
            
            # Response bekle
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    response = await asyncio.wait_for(self.response_queue.get(), timeout=0.1)
                    if response.op_code == packet.op_code + 1:  # Response op code
                        return TISResponse(
                            success=True,
                            op_code=response.op_code,
                            data=response.additional_data,
                            response_time=time.time() - start_time
                        )
                except asyncio.TimeoutError:
                    continue
                    
            return TISResponse(
                success=False,
                op_code=packet.op_code,
                error_message="Timeout"
            )
            
        except Exception as e:
            return TISResponse(
                success=False,
                op_code=packet.op_code,
                error_message=str(e)
            )
```

## 🎯 Implementation Öncelikleri

### Aşama 1: Core Infrastructure (1 hafta)
1. **core.py** - Temel data structures
2. **protocol/parser.py** - Packet parsing
3. **protocol/builder.py** - Packet building
4. **exceptions.py** - Error handling

### Aşama 2: Communication Layer (1 hafta)
1. **communication/udp_handler.py** - UDP implementation
2. **communication/manager.py** - Ana communication manager
3. **discovery/discovery.py** - Basic discovery
4. **discovery/device_mapper.py** - Device capabilities

### Aşama 3: Device Support (1 hafta)
1. **devices/base.py** - Base device class
2. **devices/lighting.py** - Lighting device support
3. **devices/climate.py** - AC/HVAC support
4. **devices/sensors.py** - Sensor support

### Aşama 4: Advanced Features (1 hafta)
1. **communication/rs485_handler.py** - RS485 support
2. Error recovery ve reconnection logic
3. Performance optimizations
4. Comprehensive testing

## 📋 Test Stratejisi

### Unit Tests
```python
# tests/test_core.py
def test_tis_packet_creation()
def test_crc_calculation()
def test_address_parsing()

# tests/test_discovery.py
def test_device_discovery()
def test_capability_mapping()

# tests/test_communication.py
def test_udp_communication()
def test_command_execution()
```

### Integration Tests
- Simülatör ile end-to-end test
- Real device validation
- Performance benchmarks

Bu yapı, mevcut TIS protocol analizi sonuçlarını kullanarak modüler, test edilebilir ve Home Assistant ile uyumlu bir kütüphane sağlar.
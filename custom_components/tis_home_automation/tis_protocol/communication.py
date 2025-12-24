"""
TIS Protocol Communication Layer
Handles UDP and RS485 communication with TIS devices.
Supports both network (UDP Port 6000) and serial (RS485) transports.
"""
from __future__ import annotations

import asyncio
import logging
import socket
import time
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, Callable, Any, Union, Tuple, AsyncGenerator

try:
    import serial
    import serial.tools.list_ports
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False

from .core import TISPacket, TISDevice, TISOpCode
from .helpers import build_packet, parse_smartcloud_packet, hexstr

_LOGGER = logging.getLogger(__name__)

# Communication constants
DEFAULT_UDP_PORT = 6000
DEFAULT_TIMEOUT = 5.0
DEFAULT_RETRY_COUNT = 3
DEFAULT_DISCOVERY_TIMEOUT = 10.0
BROADCAST_IP = "255.255.255.255"
DISCOVERY_OPCODE = [0x00, 0x0E]  # Device discovery
DISCOVERY_RESPONSE_OPCODES = [0xF004, 0x000F, 0xDA45, 0xDA44, 0x0002]  # Multiple response types

class TISCommunicationError(Exception):
    """Base exception for TIS communication errors"""
    pass

class TISTimeoutError(TISCommunicationError):
    """Timeout during communication"""
    pass

class TISConnectionError(TISCommunicationError):
    """Connection establishment failed"""
    pass

# ================== ABSTRACT BASE TRANSPORT ==================

class TISTransport(ABC):
    """Abstract base class for TIS communication transports"""
    
    def __init__(self, timeout: float = DEFAULT_TIMEOUT):
        self.timeout = timeout
        self.connected = False
        self._response_callbacks: Dict[int, Callable] = {}
        
    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """Close connection"""
        pass
    
    @abstractmethod
    async def send_packet(self, packet: List[int]) -> bool:
        """Send packet to device"""
        pass
    
    @abstractmethod
    async def receive_packet(self, timeout: Optional[float] = None) -> Optional[bytes]:
        """Receive packet from device"""
        pass
    
    @abstractmethod
    async def broadcast_discovery(self, source_ip: str) -> bool:
        """Send discovery broadcast"""
        pass
    
    def register_response_callback(self, op_code: int, callback: Callable):
        """Register callback for specific operation code responses"""
        self._response_callbacks[op_code] = callback
    
    def unregister_response_callback(self, op_code: int):
        """Unregister response callback"""
        if op_code in self._response_callbacks:
            del self._response_callbacks[op_code]

# ================== UDP TRANSPORT ==================

class TISUDPTransport(TISTransport):
    """UDP transport for TIS protocol communication (Port 6000)"""
    
    def __init__(
        self, 
        local_ip: str = "192.168.1.100", 
        port: int = DEFAULT_UDP_PORT,
        timeout: float = DEFAULT_TIMEOUT
    ):
        super().__init__(timeout)
        self.local_ip = local_ip
        self.port = port
        self.socket: Optional[socket.socket] = None
        self._receive_task: Optional[asyncio.Task] = None
        self._running = False
        
    async def connect(self) -> bool:
        """Establish UDP connection"""
        try:
            if self.connected:
                return True
                
            # Create UDP socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.socket.settimeout(self.timeout)
            
            # Bind to local address
            self.socket.bind((self.local_ip, self.port))
            
            # Start receive task
            self._running = True
            self._receive_task = asyncio.create_task(self._receive_loop())
            
            self.connected = True
            _LOGGER.info(f"UDP transport connected to {self.local_ip}:{self.port}")
            return True
            
        except Exception as e:
            _LOGGER.error(f"UDP connect failed: {e}")
            await self.disconnect()
            return False
    
    async def disconnect(self) -> bool:
        """Close UDP connection"""
        try:
            self.connected = False
            self._running = False
            
            # Cancel receive task
            if self._receive_task:
                self._receive_task.cancel()
                try:
                    await self._receive_task
                except asyncio.CancelledError:
                    pass
                self._receive_task = None
            
            # Close socket
            if self.socket:
                self.socket.close()
                self.socket = None
            
            _LOGGER.info("UDP transport disconnected")
            return True
            
        except Exception as e:
            _LOGGER.error(f"UDP disconnect failed: {e}")
            return False
    
    async def send_packet(self, packet: List[int]) -> bool:
        """Send UDP packet"""
        try:
            if not self.connected or not self.socket:
                raise TISConnectionError("UDP transport not connected")
            
            # Convert to bytes
            packet_bytes = bytes(packet)
            
            # Extract target IP from packet (first 4 bytes)
            if len(packet) >= 4:
                target_ip = f"{packet[0]}.{packet[1]}.{packet[2]}.{packet[3]}"
            else:
                target_ip = BROADCAST_IP
            
            # Send packet
            await asyncio.get_event_loop().run_in_executor(
                None, 
                self.socket.sendto, 
                packet_bytes, 
                (target_ip, self.port)
            )
            
            _LOGGER.debug(f"UDP packet sent to {target_ip}: {hexstr(packet_bytes)}")
            return True
            
        except Exception as e:
            _LOGGER.error(f"UDP send failed: {e}")
            return False
    
    async def receive_packet(self, timeout: Optional[float] = None) -> Optional[bytes]:
        """Receive UDP packet (not used in async mode, see _receive_loop)"""
        try:
            if not self.connected or not self.socket:
                return None
            
            receive_timeout = timeout or self.timeout
            self.socket.settimeout(receive_timeout)
            
            data, addr = await asyncio.get_event_loop().run_in_executor(
                None, self.socket.recvfrom, 1024
            )
            
            _LOGGER.debug(f"UDP packet received from {addr}: {hexstr(data)}")
            return data
            
        except socket.timeout:
            return None
        except Exception as e:
            _LOGGER.error(f"UDP receive failed: {e}")
            return None
    
    async def broadcast_discovery(self, source_ip: str) -> bool:
        """Send UDP discovery broadcast"""
        try:
            # Build discovery packet
            discovery_packet = build_packet(
                operation_code=DISCOVERY_OPCODE,
                ip_address=source_ip,
                source_device_id=[0x01, 0xFE],
                device_type=[0xFF, 0xFF]  # Broadcast to all device types
            )
            
            # Send as broadcast
            packet_bytes = bytes(discovery_packet)
            if self.socket:
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    self.socket.sendto,
                    packet_bytes,
                    (BROADCAST_IP, self.port)
                )
            
            _LOGGER.info(f"UDP discovery broadcast sent from {source_ip}")
            return True
            
        except Exception as e:
            _LOGGER.error(f"UDP discovery broadcast failed: {e}")
            return False
    
    async def _receive_loop(self):
        """Background task to continuously receive UDP packets"""
        try:
            while self._running and self.socket:
                try:
                    # Set a shorter timeout to avoid blocking
                    self.socket.settimeout(1.0)
                    data, addr = await asyncio.get_event_loop().run_in_executor(
                        None, self.socket.recvfrom, 1024
                    )
                    
                    _LOGGER.debug(f"UDP received {len(data)} bytes from {addr}: {data[:50]}...")
                    
                    # Parse packet
                    parsed = parse_smartcloud_packet(data)
                    if parsed and parsed.get('valid'):
                        op_code = parsed.get('op_code', 0)
                        _LOGGER.info(f"Parsed SMARTCLOUD packet: OpCode=0x{op_code:04X} from {addr}")
                        
                        # Call ALL registered callbacks for any OpCode that might be related
                        callback_called = False
                        for registered_opcode, callback in self._response_callbacks.items():
                            # Call callback for exact match OR discovery response opcodes
                            if (registered_opcode == op_code or
                                op_code in DISCOVERY_RESPONSE_OPCODES):
                                try:
                                    _LOGGER.info(f"Calling callback for OpCode 0x{op_code:04X}")
                                    if asyncio.iscoroutinefunction(callback):
                                        await callback(parsed, addr)
                                    else:
                                        callback(parsed, addr)
                                    callback_called = True
                                except Exception as e:
                                    _LOGGER.error(f"Callback error for OpCode 0x{op_code:04X}: {e}")
                        
                        if not callback_called:
                            _LOGGER.warning(f"No callback registered for OpCode 0x{op_code:04X}")
                    else:
                        _LOGGER.debug(f"Non-SMARTCLOUD packet from {addr}: {data[:20]}...")
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    if self._running:
                        _LOGGER.error(f"UDP receive loop error: {e}")
                    continue
                    
        except asyncio.CancelledError:
            pass
        except Exception as e:
            _LOGGER.error(f"UDP receive loop failed: {e}")

# ================== RS485 TRANSPORT ==================

class TISRS485Transport(TISTransport):
    """RS485 serial transport for TIS protocol communication"""
    
    def __init__(
        self, 
        port: str, 
        baudrate: int = 9600,
        timeout: float = DEFAULT_TIMEOUT
    ):
        super().__init__(timeout)
        self.port = port
        self.baudrate = baudrate
        self.serial: Optional[serial.Serial] = None
        self._receive_task: Optional[asyncio.Task] = None
        self._running = False
        
        if not HAS_SERIAL:
            raise TISCommunicationError("pyserial not installed - RS485 transport unavailable")
    
    async def connect(self) -> bool:
        """Establish RS485 connection"""
        try:
            if self.connected:
                return True
            
            # Open serial connection
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS
            )
            
            # Start receive task
            self._running = True
            self._receive_task = asyncio.create_task(self._receive_loop())
            
            self.connected = True
            _LOGGER.info(f"RS485 transport connected to {self.port}@{self.baudrate}")
            return True
            
        except Exception as e:
            _LOGGER.error(f"RS485 connect failed: {e}")
            await self.disconnect()
            return False
    
    async def disconnect(self) -> bool:
        """Close RS485 connection"""
        try:
            self.connected = False
            self._running = False
            
            # Cancel receive task
            if self._receive_task:
                self._receive_task.cancel()
                try:
                    await self._receive_task
                except asyncio.CancelledError:
                    pass
                self._receive_task = None
            
            # Close serial port
            if self.serial:
                self.serial.close()
                self.serial = None
            
            _LOGGER.info("RS485 transport disconnected")
            return True
            
        except Exception as e:
            _LOGGER.error(f"RS485 disconnect failed: {e}")
            return False
    
    async def send_packet(self, packet: List[int]) -> bool:
        """Send RS485 packet"""
        try:
            if not self.connected or not self.serial:
                raise TISConnectionError("RS485 transport not connected")
            
            # Convert to bytes
            packet_bytes = bytes(packet)
            
            # Send packet
            await asyncio.get_event_loop().run_in_executor(
                None, self.serial.write, packet_bytes
            )
            await asyncio.get_event_loop().run_in_executor(
                None, self.serial.flush
            )
            
            _LOGGER.debug(f"RS485 packet sent: {hexstr(packet_bytes)}")
            return True
            
        except Exception as e:
            _LOGGER.error(f"RS485 send failed: {e}")
            return False
    
    async def receive_packet(self, timeout: Optional[float] = None) -> Optional[bytes]:
        """Receive RS485 packet"""
        try:
            if not self.connected or not self.serial:
                return None
            
            receive_timeout = timeout or self.timeout
            
            # Wait for data with timeout
            start_time = time.time()
            while (time.time() - start_time) < receive_timeout:
                if self.serial.in_waiting > 0:
                    # Read available data
                    data = await asyncio.get_event_loop().run_in_executor(
                        None, self.serial.read, self.serial.in_waiting
                    )
                    
                    _LOGGER.debug(f"RS485 packet received: {hexstr(data)}")
                    return data
                
                await asyncio.sleep(0.01)  # Small delay
            
            return None  # Timeout
            
        except Exception as e:
            _LOGGER.error(f"RS485 receive failed: {e}")
            return None
    
    async def broadcast_discovery(self, source_ip: str) -> bool:
        """Send RS485 discovery (broadcast to serial bus)"""
        try:
            # Build discovery packet
            discovery_packet = build_packet(
                operation_code=DISCOVERY_OPCODE,
                ip_address=source_ip,
                source_device_id=[0x01, 0xFE],
                device_type=[0xFF, 0xFF]  # Broadcast to all device types
            )
            
            # Send to serial bus
            result = await self.send_packet(discovery_packet)
            
            _LOGGER.info(f"RS485 discovery broadcast sent from {source_ip}")
            return result
            
        except Exception as e:
            _LOGGER.error(f"RS485 discovery broadcast failed: {e}")
            return False
    
    async def _receive_loop(self):
        """Background task to continuously receive RS485 packets"""
        try:
            while self._running and self.serial:
                try:
                    data = await self.receive_packet(1.0)  # 1 second timeout
                    
                    if data:
                        # Parse packet
                        parsed = parse_smartcloud_packet(data)
                        if parsed.get('valid'):
                            op_code = parsed.get('op_code', 0)
                            
                            # Call registered callback if exists
                            if op_code in self._response_callbacks:
                                callback = self._response_callbacks[op_code]
                                if asyncio.iscoroutinefunction(callback):
                                    asyncio.create_task(callback(parsed, None))
                                else:
                                    callback(parsed, None)
                    
                except Exception as e:
                    if self._running:
                        _LOGGER.error(f"RS485 receive loop error: {e}")
                    continue
                    
        except asyncio.CancelledError:
            pass
        except Exception as e:
            _LOGGER.error(f"RS485 receive loop failed: {e}")

# ================== COMMUNICATION MANAGER ==================

class TISCommunicationManager:
    """High-level communication manager for TIS devices"""
    
    def __init__(self):
        self.transports: List[TISTransport] = []
        self.discovered_devices: Dict[str, TISDevice] = {}
        self.active_transport: Optional[TISTransport] = None
        self._discovery_callbacks: List[Callable] = []
        
    def add_transport(self, transport: TISTransport):
        """Add a transport to the manager"""
        self.transports.append(transport)
        
        # Register discovery response callbacks for all OpCodes
        for response_opcode in DISCOVERY_RESPONSE_OPCODES:
            transport.register_response_callback(
                response_opcode,
                self._handle_discovery_response
            )
    
    def add_discovery_callback(self, callback: Callable):
        """Add callback for discovered devices"""
        self._discovery_callbacks.append(callback)
    
    async def connect_all(self) -> Dict[str, bool]:
        """Connect all transports"""
        results = {}
        
        for i, transport in enumerate(self.transports):
            transport_name = f"{transport.__class__.__name__}_{i}"
            results[transport_name] = await transport.connect()
            
            # Set first successful transport as active
            if results[transport_name] and not self.active_transport:
                self.active_transport = transport
        
        return results
    
    async def disconnect_all(self) -> Dict[str, bool]:
        """Disconnect all transports"""
        results = {}
        
        for i, transport in enumerate(self.transports):
            transport_name = f"{transport.__class__.__name__}_{i}"
            results[transport_name] = await transport.disconnect()
        
        self.active_transport = None
        return results
    
    @asynccontextmanager
    async def connection_context(self) -> AsyncGenerator[TISCommunicationManager, None]:
        """Context manager for automatic connection/disconnection"""
        try:
            await self.connect_all()
            yield self
        finally:
            await self.disconnect_all()
    
    async def discover_devices(
        self,
        source_ip: str = "192.168.1.100",
        timeout: float = 30.0  # Extended timeout like rs485_tis_gui_tester.py
    ) -> Dict[str, TISDevice]:
        """Discover TIS devices using EXACT strategy from working rs485_tis_gui_tester.py"""
        
        # Clear previous discoveries
        self.discovered_devices.clear()
        
        # Discovery operation codes from working rs485_tis_gui_tester.py (EXACT ORDER)
        discovery_opcodes = [0xF003, 0x000E, 0xDA44, 0x0002]
        
        if not self.transports:
            _LOGGER.warning("No transports available for discovery")
            return {}
        
        connected_transports = [t for t in self.transports if t.connected]
        if not connected_transports:
            _LOGGER.warning("No connected transports for discovery")
            return {}
        
        _LOGGER.info(f"🔍 Starting TIS device discovery (rs485_tis_gui_tester.py strategy)")
        _LOGGER.info(f"📡 Discovery OpCodes: {[f'0x{op:04X}' for op in discovery_opcodes]}")
        
        # Send each discovery OpCode with proper intervals (EXACT like rs485_tis_gui_tester.py)
        for i, op_code in enumerate(discovery_opcodes):
            _LOGGER.info(f"📤 Sending discovery OpCode 0x{op_code:04X} ({i+1}/{len(discovery_opcodes)})")
            
            # Send discovery packet with this OpCode
            for transport in connected_transports:
                await self._send_discovery_opcode(transport, source_ip, op_code)
            
            # Wait between OpCodes (EXACT like original: 1 second intervals)
            if i < len(discovery_opcodes) - 1:
                await asyncio.sleep(1.0)  # 1 second between different OpCodes
        
        # Main timeout wait (EXACT like rs485_tis_gui_tester.py)
        _LOGGER.info(f"⏳ Discovery packets sent, waiting {timeout}s for responses...")
        await asyncio.sleep(timeout)
        
        # Extended wait for late 000F responses (EXACT like rs485_tis_gui_tester.py: 8+ seconds)
        if 0x000E in discovery_opcodes:
            _LOGGER.info("⏳ Waiting additional 8s for late 000F responses (device names)...")
            await asyncio.sleep(8.0)  # Extended wait like rs485_tis_gui_tester.py
        
        # Final wait for any remaining responses (EXACT like rs485_tis_gui_tester.py)
        _LOGGER.info("⏳ Final wait (5s) for remaining responses...")
        await asyncio.sleep(5.0)  # Final wait like rs485_tis_gui_tester.py
        
        _LOGGER.info(f"✅ Discovery completed. Found {len(self.discovered_devices)} devices")
        for device_key, device in self.discovered_devices.items():
            _LOGGER.info(f"   📱 {device_key}: {device.name} (Type: 0x{device.device_type:04X})")
        
        return self.discovered_devices.copy()
    
    async def _send_discovery_opcode(self, transport: TISTransport, source_ip: str, op_code: int) -> bool:
        """Send discovery packet with specific OpCode (based on rs485_tis_gui_tester.py)"""
        try:
            # Build discovery packet for this OpCode
            discovery_packet = build_packet(
                operation_code=[(op_code >> 8) & 0xFF, op_code & 0xFF],
                ip_address=source_ip,
                device_id=[0xFF, 0xFF],  # Broadcast target
                source_device_id=[0x01, 0xFE],  # Scanner device ID (like original)
                device_type=[0xFF, 0xFE],  # Light Dimmer type (like original - 0xFFFE)
                additional_packets=[]
            )
            
            # Send packet
            result = await transport.send_packet(discovery_packet)
            if result:
                _LOGGER.debug(f"Discovery OpCode 0x{op_code:04X} sent via {transport.__class__.__name__}")
            else:
                _LOGGER.warning(f"Failed to send discovery OpCode 0x{op_code:04X} via {transport.__class__.__name__}")
            
            return result
            
        except Exception as e:
            _LOGGER.error(f"Error sending discovery OpCode 0x{op_code:04X}: {e}")
            return False
    
    async def send_to_device(
        self,
        device_id: List[int],
        op_code: List[int], 
        source_ip: str = "192.168.1.100",
        additional_data: List[int] = None,
        transport: Optional[TISTransport] = None
    ) -> bool:
        """Send packet to specific device"""
        
        target_transport = transport or self.active_transport
        if not target_transport or not target_transport.connected:
            _LOGGER.error("No active transport for sending")
            return False
        
        # Build packet
        packet = build_packet(
            operation_code=op_code,
            ip_address=source_ip,
            device_id=device_id,
            additional_packets=additional_data or []
        )
        
        return await target_transport.send_packet(packet)
    
    async def _handle_discovery_response(self, parsed_packet: Dict, source_addr: Any):
        """Handle discovery response packets - IMPROVED VERSION"""
        try:
            _LOGGER.info(f"Processing discovery response: {parsed_packet}")
            
            # Extract device information
            device_id = parsed_packet.get('source_device', [0x00, 0x00])
            device_type = parsed_packet.get('device_type', 0xFFFF)
            op_code = parsed_packet.get('op_code', 0x0000)
            additional_data = parsed_packet.get('additional_data', b'')
            ip_address = parsed_packet.get('ip', "")
            
            _LOGGER.info(f"Device info: ID={device_id}, Type=0x{device_type:04X}, OpCode=0x{op_code:04X}, IP={ip_address}")
            
            # Try to decode device name from additional_data
            device_name = ""
            if additional_data:
                try:
                    # Try UTF-8 first, then ASCII
                    try:
                        device_name = additional_data.decode('utf-8', errors='ignore').rstrip('\x00').strip()
                    except:
                        device_name = additional_data.decode('ascii', errors='ignore').rstrip('\x00').strip()
                    
                    if device_name:
                        _LOGGER.info(f"Decoded device name: '{device_name}'")
                except Exception as e:
                    _LOGGER.warning(f"Device name decode error: {e}")
            
            # Create device key (using source_device as key)
            device_key = f"{device_id[0]:02X}{device_id[1]:02X}"
            
            # Get device type name from our mapping (if available)
            device_type_name = "Unknown"
            try:
                # This would require our device type mapping
                device_type_name = f"Type_0x{device_type:04X}"
            except:
                pass
            
            # Create final device name
            final_device_name = device_name if device_name else f"TIS {device_type_name} ({device_key})"
            
            # Create or update TIS device
            device = TISDevice(
                device_id=device_id,
                device_type=device_type,
                name=final_device_name,
                ip_address=ip_address,
                source_address=source_addr
            )
            
            # Store discovered device (update if exists)
            self.discovered_devices[device_key] = device
            
            _LOGGER.info(f"🔍 DEVICE DISCOVERED: '{device.name}' ({device_key}) Type: 0x{device_type:04X} IP: {ip_address}")
            
            # Notify discovery callbacks
            for callback in self._discovery_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(device)  # Use await instead of create_task for immediate execution
                    else:
                        callback(device)
                except Exception as e:
                    _LOGGER.error(f"Discovery callback error: {e}")
                    
        except Exception as e:
            _LOGGER.error(f"Discovery response handling error: {e}")
            import traceback
            _LOGGER.error(f"Traceback: {traceback.format_exc()}")

# ================== UTILITY FUNCTIONS ==================

def get_available_serial_ports() -> List[str]:
    """Get list of available serial ports"""
    if not HAS_SERIAL:
        return []
    
    try:
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]
    except Exception as e:
        _LOGGER.error(f"Failed to get serial ports: {e}")
        return []

def get_local_ip() -> str:
    """Get local IP address"""
    try:
        # Connect to remote server to determine local IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "192.168.1.100"  # Fallback

async def create_communication_manager(
    udp_config: Optional[Dict] = None,
    serial_config: Optional[Dict] = None
) -> TISCommunicationManager:
    """Create and configure communication manager with transports"""
    
    manager = TISCommunicationManager()
    
    # Add UDP transport if configured
    if udp_config:
        udp_transport = TISUDPTransport(
            local_ip=udp_config.get("local_ip", get_local_ip()),
            port=udp_config.get("port", DEFAULT_UDP_PORT),
            timeout=udp_config.get("timeout", DEFAULT_TIMEOUT)
        )
        manager.add_transport(udp_transport)
    
    # Add RS485 transport if configured and available
    if serial_config and HAS_SERIAL:
        rs485_transport = TISRS485Transport(
            port=serial_config.get("port"),
            baudrate=serial_config.get("baudrate", 9600),
            timeout=serial_config.get("timeout", DEFAULT_TIMEOUT)
        )
        manager.add_transport(rs485_transport)
    
    return manager

# ================== EXPORTS ==================

__all__ = [
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
    
    # Constants
    'DEFAULT_UDP_PORT',
    'DEFAULT_TIMEOUT',
    'DEFAULT_RETRY_COUNT',
    'DEFAULT_DISCOVERY_TIMEOUT',
    'BROADCAST_IP',
    'DISCOVERY_OPCODE',
    'DISCOVERY_RESPONSE_OPCODE'
]
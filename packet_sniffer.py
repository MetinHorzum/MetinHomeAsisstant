#!/usr/bin/env python3
"""
TIS Packet Sniffer - Discovery paketlerini yakalar
"""

import socket
import sys
import os
from datetime import datetime

sys.path.append('../../Downloads')
try:
    from tis_protocol_helper import parse_smartcloud_packet
    PARSER_AVAILABLE = True
except ImportError:
    PARSER_AVAILABLE = False

def hexstr(data):
    return " ".join(f"{b:02X}" for b in data)

def start_sniffer():
    """UDP Port 6000'i dinle"""
    print("📡 TIS Packet Sniffer Started")
    print("🎯 Listening on UDP Port 6000...")
    print("🔍 Yakalanan paketler aşağıda görünecek...")
    print("=" * 60)
    
    try:
        # UDP socket oluştur
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('0.0.0.0', 6000))
        sock.settimeout(1.0)
        
        packet_count = 0
        discovery_count = 0
        
        while True:
            try:
                data, addr = sock.recvfrom(1024)
                packet_count += 1
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                
                print(f"\n📦 Packet #{packet_count} [{timestamp}]")
                print(f"📍 From: {addr[0]}:{addr[1]}")
                print(f"📏 Size: {len(data)} bytes")
                print(f"🔢 Raw: {hexstr(data)}")
                
                # TIS paketi mi kontrol et
                if PARSER_AVAILABLE and len(data) >= 20:
                    try:
                        parsed = parse_smartcloud_packet(data)
                        if parsed.get('valid'):
                            op_code = parsed.get('op_code', 0)
                            print(f"✅ TIS Packet:")
                            print(f"   • OpCode: 0x{op_code:04X}")
                            print(f"   • Source: {parsed.get('source_device', 'N/A')}")
                            print(f"   • Target: {parsed.get('target_device', 'N/A')}")
                            print(f"   • Device Type: 0x{parsed.get('device_type', 0):04X}")
                            
                            # Discovery paketleri
                            if op_code in [0x000E, 0x000F, 0xF003, 0xF004, 0xDA44, 0x0002]:
                                discovery_count += 1
                                print(f"🔍 DISCOVERY PACKET! (#{discovery_count})")
                                
                                if 'additional_data' in parsed:
                                    add_data = parsed['additional_data']
                                    if add_data:
                                        # Device name çıkarma
                                        try:
                                            device_name = add_data.decode('ascii', errors='ignore').rstrip('\x00')
                                            if device_name:
                                                print(f"   • Device Name: '{device_name}'")
                                        except:
                                            pass
                        else:
                            print(f"❌ Invalid TIS packet: {parsed.get('error', 'Unknown')}")
                    except Exception as e:
                        print(f"⚠️ Parse error: {e}")
                
                # ASCII içeriği kontrol et
                ascii_content = ""
                for b in data:
                    if 32 <= b <= 126:  # Printable ASCII
                        ascii_content += chr(b)
                    else:
                        ascii_content += "."
                
                if any(c.isalpha() for c in ascii_content):
                    print(f"📝 ASCII: {ascii_content}")
                
                print("-" * 60)
                
            except socket.timeout:
                continue
            except KeyboardInterrupt:
                print(f"\n🛑 Sniffer durduruldu")
                print(f"📊 Toplam: {packet_count} paket, {discovery_count} discovery")
                break
            except Exception as e:
                print(f"❌ Sniffer hatası: {e}")
                continue
                
    except Exception as e:
        print(f"❌ Socket hatası: {e}")
        print("💡 Port 6000 başka bir uygulama tarafından kullanılıyor olabilir")

if __name__ == "__main__":
    print("🚀 TIS Packet Sniffer")
    print("⚠️ Bu aracı çalıştırmadan önce Home Assistant'ı durdurun!")
    print("💡 Port 6000 çakışmasını önlemek için...")
    input("Hazır olduğunuzda ENTER'a basın...")
    
    start_sniffer()
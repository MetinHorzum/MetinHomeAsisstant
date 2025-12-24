# TIS Home Automation Debug Rehberi

## 🐛 Cihaz Bulunamıyor Sorunu Çözümü

### 1. Home Assistant Loglarını Kontrol Edin

**configuration.yaml'a debug logging ekleyin:**
```yaml
logger:
  default: info
  logs:
    custom_components.tis_home_automation: debug
    custom_components.tis_home_automation.tis_protocol: debug
```

Home Assistant'ı restart edin ve logları kontrol edin:
```bash
tail -f /config/home-assistant.log | grep tis
```

### 2. Manual Cihaz Keşfi Test

**Developer Tools → Services**'da şu servisi çalıştırın:

```yaml
service: tis_home_automation.discover_devices  
data:
  timeout: 60
```

### 3. Raw Command Test

**Test komutu gönder:**
```yaml
service: tis_home_automation.send_raw_command
data:
  device_id: "FFFF"  # Broadcast
  op_code: "000E"    # Discovery command
```

### 4. Network Debug

**UDP portunu kontrol edin:**
```bash
netstat -an | grep 6000
```

**Firewall kontrolü (Windows):**
```cmd
netsh advfirewall firewall show rule name=all | findstr 6000
```

**Firewall rule ekleyin:**
```cmd
netsh advfirewall firewall add rule name="TIS Home Automation" dir=in action=allow protocol=UDP localport=6000
```

### 5. Mock Test Sistemi

**Mock cihazları test etmek için:**

```python
# Developer Tools → Template'da test edin:
{% set mock_devices = [
  {"device_id": "0001", "device_type": "0101", "name": "Test Switch"},
  {"device_id": "0002", "device_type": "0201", "name": "Test Light"}
] %}
{{ mock_devices }}
```

### 6. Integration Debug Modu

**config_flow.py'da debug mode ekleyin:**

Home Assistant'ın `/config/custom_components/tis_home_automation/` klasöründe:

**debug_config.yaml oluşturun:**
```yaml
debug_mode: true
mock_devices:
  - device_id: "0001"
    device_type: "0101" 
    name: "Debug Switch 1"
    ip_address: "192.168.1.100"
  - device_id: "0002"
    device_type: "0201"
    name: "Debug Light 1"
    ip_address: "192.168.1.101"
```

### 7. Manuel Integration Test

**Integration'ı manuel test edin:**

```python
# Home Assistant Python shell'de:
from custom_components.tis_home_automation.tis_protocol import get_local_ip
print(f"Local IP: {get_local_ip()}")

from custom_components.tis_home_automation.tis_protocol.communication import create_communication_manager
comm = create_communication_manager("udp", host="192.168.1.100", port=6000)
print(f"Communication Manager: {comm}")
```

### 8. Expected Log Messages

**Başarılı durumda görmeli olduğunuz loglar:**
```
[tis_home_automation] TIS Communication Manager initialized
[tis_home_automation] Starting device discovery...
[tis_home_automation] Local IP detected: 192.168.1.xxx
[tis_home_automation] Listening on UDP port 6000
[tis_home_automation] Discovery packet sent: 000E
[tis_home_automation] Device discovered: ID=0001, Type=0101
```

**Hata durumunda görebileceğiniz loglar:**
```
[tis_home_automation] ERROR: Cannot bind to port 6000
[tis_home_automation] ERROR: No network interface found  
[tis_home_automation] ERROR: Discovery timeout after 30s
[tis_home_automation] WARNING: No TIS devices responded
```

### 9. Quick Fix Commands

**Integration'ı yeniden yükle:**
1. Settings → Integrations
2. TIS Home Automation → "..." → Remove
3. Restart Home Assistant  
4. Add Integration tekrar

**Hard reset:**
```bash
# Home Assistant'ı durdur
rm -rf /config/.storage/core.config_entries
# Home Assistant'ı başlat - tüm integrationlar sıfırlanır
```

### 10. Test Cihazı Simülasyonu

Gerçek TIS cihazınız yoksa, test için basit UDP server kurabilirsiniz:

**test_server.py:**
```python
import socket
import time

def create_test_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', 6000))
    
    print("TIS Test Server listening on port 6000...")
    
    while True:
        data, addr = sock.recvfrom(1024)
        print(f"Received from {addr}: {data.hex()}")
        
        # Discovery response simülasyonu
        if data.hex().startswith('000e'):  # Discovery command
            # Mock response: Device ID 0001, Type 0101
            response = bytes.fromhex('000F00010101')
            sock.sendto(response, addr)
            print(f"Sent response: {response.hex()}")

if __name__ == "__main__":
    create_test_server()
```

Bu debug adımlarını takip ederek sorunun nereden kaynaklandığını bulabilirsiniz!
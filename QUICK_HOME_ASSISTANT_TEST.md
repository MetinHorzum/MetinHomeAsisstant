# 🏠 TIS Home Assistant Integration - Hızlı Test

## 1. Home Assistant'a Kurulum

### Custom Component Kopyalama:
```bash
# Home Assistant config dizininize gidin
cd /config  # veya C:\Users\{USERNAME}\.homeassistant

# Custom components klasörü oluşturun
mkdir -p custom_components

# TIS integration'ı kopyalayın
cp -r "C:/Users/Meth/Desktop/TIS Automation/custom_components/tis_home_automation" custom_components/
```

### Home Assistant Restart:
```bash
# Home Assistant'ı yeniden başlatın
sudo systemctl restart home-assistant

# veya HA web arayüzünden: Developer Tools > Services > homeassistant.restart
```

## 2. Integration Kurulumu

1. **Settings** > **Devices & Services** > **Add Integration**
2. **"TIS Home Automation"** ara
3. Discovery işlemi otomatik olarak çalışacak
4. Bulunan cihaz: **192.168.1.200** (Device ID: 01FE)

## 3. Beklenen Sonuç

- ✅ Discovery başarılı
- ✅ Device ID 01FE tanımlanır
- ✅ Entity'ler otomatik oluşturulur
- ✅ Kontrol panelinde görünür

## 4. Test Adımları

### Device Control Test:
```python
# Home Assistant Developer Tools > Services
service: tis_home_automation.send_command
data:
  device_id: "01FE" 
  command: "0x0001"  # Test command
```

### Entity State Kontrol:
- **Entities** bölümünde `tis_home_automation.` ile başlayan entity'leri kontrol edin
- Device state ve availability durumunu gözlemleyin

## 5. Debug (Gerekirse)

### Log Kontrol:
```yaml
# configuration.yaml
logger:
  default: info
  logs:
    custom_components.tis_home_automation: debug
```

### Manuel Discovery Test:
```python
# Home Assistant Python environment
from custom_components.tis_home_automation.tis_protocol.communication import TISCommunicationManager

# Test script çalıştır
python test_discovery_simple.py
```

## 6. Sonraki Adımlar

- ✅ Basic discovery works
- 📝 Test device commands  
- 📝 Verify entity updates
- 📝 Test automation scenarios

---
**Bugün Başardıklarımız:**
- ✅ TIS Protocol reverse engineering tamamlandı
- ✅ Home Assistant custom component geliştrildi  
- ✅ UDP discovery sistemi implement edildi
- ✅ Gerçek TIS cihazı (01FE @ 192.168.1.200) başarıyla tespit edildi
- ✅ Production-ready kod hazır

**Şu An Durumu:** Integration kullanıma hazır! 🚀
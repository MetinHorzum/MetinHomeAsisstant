# TIS Home Automation - Installation Guide

## "Invalid handler specified" Hatasını Çözme Rehberi

### Sorun
TIS Home Automation entegrasyonunu yüklediğinizde şu hatayı alabilirsiniz:
```
Yapılandırma akışı yüklenemedi: {"message":"Invalid handler specified"}
```

### Çözüm Adımları

#### 1. Doğru Kurulum Kontrolü
Integration'ınızın doğru dizinde olduğundan emin olun:
```
/config/custom_components/tis_home_automation/
├── __init__.py
├── manifest.json
├── config_flow.py
├── const.py
├── coordinator.py
├── switch.py
├── light.py
├── climate.py
├── sensor.py
├── binary_sensor.py
└── tis_protocol/
    ├── __init__.py
    ├── core.py
    ├── helpers.py
    └── communication.py
```

#### 2. Home Assistant'ı Tamamen Restart Edin
```bash
# Home Assistant Core için
sudo systemctl restart home-assistant

# Home Assistant Supervised/OS için
# Settings > System > Restart > Restart Home Assistant
```

**ÖNEMLİ:** Sadece "Quick Reload" yeterli değil, tam restart gerekli!

#### 3. Browser Cache Temizleme
- Chrome/Edge: `Ctrl+Shift+R` veya `F12` > Network > "Disable cache" 
- Firefox: `Ctrl+Shift+R`
- Safari: `Cmd+Shift+R`

#### 4. Integration Cache Temizleme
Home Assistant CLI erişiminiz varsa:
```bash
# Home Assistant cache'ini temizle
rm -rf /config/.storage/core.config_entries
# Sadece problem yaşıyorsanız - BU RİSKLİ!
```

#### 5. Home Assistant Log Kontrolü
`/config/home-assistant.log` dosyasını kontrol edin:
```bash
tail -f /config/home-assistant.log | grep tis_home_automation
```

Şu gibi hatalar arıyın:
- Import errors
- Missing dependencies  
- Config flow registration errors

### Yaygın Sorunlar ve Çözümler

#### A. "No module named 'tis_protocol'" Hatası
**Sorun:** TIS protocol modülü bulunamıyor
**Çözüm:** 
1. `tis_protocol/` klasörünün mevcut olduğunu kontrol edin
2. `tis_protocol/__init__.py` dosyasının var olduğunu kontrol edin
3. Home Assistant'ı restart edin

#### B. "No module named 'pyserial'" Hatası  
**Sorun:** RS485 desteği için pyserial gerekli
**Çözüm:**
```bash
# Home Assistant Core için
pip install pyserial

# Home Assistant OS/Supervised kullanıyorsanız:
# Settings > Add-ons > SSH & Web Terminal
# Terminal'de: pip install pyserial
```

#### C. Integration Gözükmüyor
**Sorun:** Settings > Integrations'da TIS gözükmüyor
**Çözüm:**
1. `manifest.json` dosyasındaki `domain` değerini kontrol edin
2. `config_flow = true` olduğunu kontrol edin  
3. Home Assistant'ı restart edin
4. Hard refresh yapın (`Ctrl+Shift+R`)

### Adım Adım Test Prosedürü

#### Adım 1: Dosya Yapısı Kontrolü
```bash
ls -la /config/custom_components/tis_home_automation/
# Tüm dosyaların mevcut olduğunu kontrol edin
```

#### Adım 2: Home Assistant Restart
```bash
sudo systemctl restart home-assistant
# Veya UI'dan: Settings > System > Restart
```

#### Adım 3: Integration Ekleme
1. Settings > Devices & Services > Add Integration
2. "TIS Home Automation" ara
3. Eğer bulamazsa F5 ile refresh edin

#### Adım 4: Konfigürasyon
1. UDP veya RS485 seçin
2. Network ayarlarını girin (UDP için):
   - Local IP: 192.168.1.22 (sizin IP'niz)
   - Port: 6000
3. Discovery'ye izin verin (30+ saniye)

### Başarılı Kurulum Belirtileri

Integration başarıyla yüklendiğinde:
- ✅ Settings > Integrations'da "TIS Home Automation" görünür
- ✅ Discovery sırasında TIS cihazları bulunur
- ✅ Entities sekmesinde TIS cihazları listelenir
- ✅ Loglar'da başarı mesajları görünür:
  ```
  TIS Home Automation integration setup completed successfully
  Discovery completed: found X devices
  ```

### Troubleshooting

#### Problem: "Handler kayıtlı değil" hatası
**Çözüm:**
```python
# custom_components/tis_home_automation/config_flow.py kontrol edin
class TISConfigFlow(config_entries.ConfigFlow):
    domain = DOMAIN  # Bu satır olmalı
    VERSION = 1
```

#### Problem: Import hatası
**Çözüm:**
```python
# custom_components/tis_home_automation/__init__.py kontrol edin  
DOMAIN = "tis_home_automation"
```

### İletişim ve Destek

Sorun devam ederse:
1. Home Assistant log dosyasını kontrol edin
2. GitHub Issues'da sorun bildirin
3. Discord/Forum'da yardım isteyin

**Log Örneği:**
```bash
tail -n 100 /config/home-assistant.log | grep -i tis
```

### Başarılı Test Koşulları

Bu integration şu koşullar altında test edilmiştir:
- ✅ Home Assistant OS 2024.12
- ✅ Home Assistant Core 2024.12+  
- ✅ Network: 192.168.1.x (UDP Port 6000)
- ✅ Gerçek TIS cihazları: 12+ device discovery
- ✅ Device types: Mekanik, Mutfak, Toplantı Odası, AR-GE, vb.

Installation başarıyla tamamlandığında TIS entegrasyonu tam fonksiyonel olacaktır!
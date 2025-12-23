# TIS Home Automation - Home Assistant Integration

TIS akıllı ev cihazları için kapsamlı Home Assistant entegrasyonu. Bu entegrasyon, TIS protokolünü kullanarak 150+ farklı cihaz tipini destekler ve hem UDP hem de RS485 haberleşme seçenekleri sunar.

## 🎯 Özellikler

### 📡 İletişim Desteği
- **UDP Network (Port 6000)**: Ağ üzerinden haberleşme
- **RS485 Serial**: Seri port üzerinden doğrudan bağlantı
- **Otomatik Cihaz Keşfi**: SMARTCLOUD protokolü ile cihaz tespiti
- **Çift Transport**: Aynı anda hem UDP hem RS485 desteği

### 🏠 Desteklenen Cihazlar
- **Anahtar**: 1-4 gang anahtarlar, sahne kontrolleri
- **Dimmer**: 1-2 gang dimmerlar, RGB/tunable white
- **Klima**: AC kontrolleri, termostatlar, yerden ısıtma
- **Sensörler**: Sıcaklık, nem, hareket, kapı/pencere, duman, gaz
- **Sağlık Sensörleri**: Işık, gürültü, eCO2, TVOC, hava kalitesi
- **Güvenlik**: Alarm sistemleri, kameralar
- **Ses/Görüntü**: TV, ses sistemi kontrolleri

### 🛠 Gelişmiş Özellikler
- **Asenkron İletişim**: Non-blocking haberleşme
- **CRC Doğrulama**: Paket bütünlüğü kontrolü
- **Cihaz Sağlığı**: Online/offline takibi
- **Özel Servisler**: Ham komut gönderme, cihaz sıfırlama
- **Çoklu Dil**: Türkçe ve İngilizce destekli
- **HACS Entegrasyonu**: Kolay kurulum ve güncelleme

## 🚀 Kurulum

### Yöntem 1: HACS (Önerilen)

1. HACS'i açın
2. **Integrations** sekmesine gidin
3. Sağ üst köşeden **⋮** menüsüne tıklayın
4. **Custom repositories** seçin
5. Repository URL'ini ekleyin: `https://github.com/your-username/tis-home-automation`
6. Category: **Integration**
7. **TIS Home Automation** entegrasyonunu bulup yükleyin
8. Home Assistant'ı yeniden başlatın

### Yöntem 2: Manuel Kurulum

1. Bu repository'yi indirin
2. `custom_components/tis_home_automation` klasörünü Home Assistant'ın `custom_components` dizinine kopyalayın
3. `tis_protocol` klasörünü de aynı dizine kopyalayın
4. Gerekli bağımlılıkları yükleyin:
   ```bash
   pip install pyserial
   ```
5. Home Assistant'ı yeniden başlatın

## ⚙️ Yapılandırma

### 1. Entegrasyon Ekleme

1. **Ayarlar** > **Cihazlar ve Servisler**'e gidin
2. **Entegrasyon Ekle**'ye tıklayın
3. **TIS Home Automation**'ı arayın ve seçin

### 2. İletişim Türü Seçimi

**UDP Ağ İletişimi:**
- Yerel IP adresi: Home Assistant sunucunuzun IP'si
- Port: 6000 (varsayılan)
- Çoğu kurulum için önerilen seçenek

**RS485 Seri İletişim:**
- Seri port: RS485 adaptörünüzün portu (örn. `/dev/ttyUSB0`)
- Baud hızı: 9600 (varsayılan)
- Doğrudan kablo bağlantısı gerektirir

### 3. Cihaz Keşfi

- Keşif süresini ayarlayın (5-120 saniye)
- Entegrasyon otomatik olarak TIS cihazlarını bulacak
- Bulunan cihazlar otomatik olarak uygun platform'lara eklenecek

## 📱 Kullanım

### Temel Entity'ler

**Anahtar (Switch):**
```yaml
# Tek gang anahtar
switch.tis_switch_01fe

# Çoklu gang anahtar  
switch.tis_switch_gang_1_02fe
switch.tis_switch_gang_2_02fe
```

**Dimmer (Light):**
```yaml
# Dimmer kontrolü
light.tis_dimmer_03fe
# Brightness: 0-255
# Renk desteği (RGB modeller için)
```

**Klima (Climate):**
```yaml
# AC kontroller
climate.tis_ac_04fe
# Modes: cool, heat, fan_only, auto, off
# Temperature: 16-30°C
# Fan speeds: auto, low, medium, high
```

**Sensör (Sensor):**
```yaml
# Sıcaklık sensörü
sensor.tis_temperature_05fe

# Sağlık sensörü (6 ayrı sensör)
sensor.tis_health_sensor_lux_06fe
sensor.tis_health_sensor_noise_06fe  
sensor.tis_health_sensor_eco2_06fe
sensor.tis_health_sensor_tvoc_06fe
sensor.tis_health_sensor_temperature_06fe
sensor.tis_health_sensor_humidity_06fe
```

### Özel Servisler

**Cihaz Keşfi:**
```yaml
service: tis_home_automation.discover_devices
data:
  source_ip: "192.168.1.100"  # isteğe bağlı
  timeout: 30  # saniye
```

**Ham Komut Gönderme:**
```yaml
service: tis_home_automation.send_raw_command  
data:
  device_id: "01FE"  # hex string veya [1, 254]
  op_code: "1101"    # hex string veya [17, 1]  
  additional_data: [50]  # isteğe bağlı
```

**Klima Kontrolü:**
```yaml
service: tis_home_automation.ac_control
data:
  device_id: "04FE"
  power: "on"
  mode: "cool" 
  temperature: 22
  fan_speed: "medium"
```

**Aydınlatma Kontrolü:**
```yaml
service: tis_home_automation.lighting_control
data:
  device_id: "03FE"
  power: "on"
  brightness: 75  # 0-100%
  gang_index: 0   # çoklu gang için
```

## 🔧 Gelişmiş Yapılandırma

### Services.yaml Örnekleri

```yaml
# Sabah rutini
morning_routine:
  sequence:
    - service: tis_home_automation.lighting_control
      data:
        device_id: "01FE"
        power: "on" 
        brightness: 80
    - service: tis_home_automation.ac_control
      data:
        device_id: "04FE"
        power: "on"
        mode: "cool"
        temperature: 24

# Gece modu
night_mode:
  sequence:
    - service: tis_home_automation.lighting_control
      data:
        device_id: "01FE"
        brightness: 10
    - service: tis_home_automation.ac_control
      data:
        device_id: "04FE"
        mode: "auto"
        temperature: 26
```

### Otomasyonlar

```yaml
# Hareket algılandığında ışığı aç
automation:
  - alias: "TIS Motion Light"
    trigger:
      platform: state
      entity_id: binary_sensor.tis_motion_07fe
      to: "on"
    action:
      service: switch.turn_on
      entity_id: switch.tis_switch_01fe

# Sıcaklık çok yüksek olduğunda klimayı aç  
  - alias: "TIS Auto AC"
    trigger:
      platform: numeric_state
      entity_id: sensor.tis_temperature_05fe
      above: 28
    action:
      service: tis_home_automation.ac_control
      data:
        device_id: "04FE"
        power: "on"
        mode: "cool"
        temperature: 24
```

## 🐛 Sorun Giderme

### Yaygın Sorunlar

**Cihazlar bulunamıyor:**
- IP adresi ve port ayarlarını kontrol edin
- Ağ bağlantısını doğrulayın
- Güvenlik duvarı ayarlarını kontrol edin
- TIS cihazlarının aynı ağda olduğundan emin olun

**Seri port bağlantı hatası:**
- Seri port adresini kontrol edin (`ls /dev/tty*`)
- Kullanıcı izinlerini kontrol edin (`sudo usermod -a -G dialout homeassistant`)
- RS485 adaptörünün düzgün takıldığından emin olun
- Baud hızının cihazlarla eşleştiğinden emin olun

**Cihazlar yanıt vermiyor:**
- Cihaz online durumunu kontrol edin
- CRC hatalarını log'lardan takip edin
- Cihazı yeniden başlatmayı deneyin
- Sinyallerin güçlü olduğundan emin olun

### Debug Modu

```yaml
# configuration.yaml
logger:
  default: info
  logs:
    custom_components.tis_home_automation: debug
    tis_protocol: debug
```

## 📊 Desteklenen Cihaz Tipleri

| Kategori | Cihaz Tipi | OpCode | Açıklama |
|----------|------------|--------|----------|
| **Aydınlatma** | Switch 1-4 Gang | 0x0100-0x0103 | Basit anahtar |
| | Dimmer 1-2 Gang | 0x0110-0x0111 | Dimmer kontrolü |  
| | Curtain Switch | 0x0120 | Perde kontrolü |
| | Scene Switch | 0x0130 | Sahne kontrolü |
| **İklim** | AC Controller | 0x0200 | Klima kontrolü |
| | Thermostat | 0x0201 | Termostat |
| | Floor Heating | 0x0202 | Yerden ısıtma |
| | Fan Controller | 0x0210 | Fan kontrolü |
| **Sensör** | Motion Sensor | 0x0300 | Hareket algılayıcı |
| | Door/Window | 0x0301 | Kapı/pencere sensörü |
| | Temperature | 0x0302 | Sıcaklık sensörü |
| | Humidity | 0x0303 | Nem sensörü |
| | Light Sensor | 0x0304 | Işık sensörü |
| | Health Sensor | 0x0310 | 6-in-1 sensör |
| **Güvenlik** | Door Lock | 0x0400 | Akıllı kilit |
| | Alarm Panel | 0x0401 | Alarm paneli |
| | Smoke Detector | 0x0305 | Duman dedektörü |

## 🤝 Katkı

Katkılarınızı bekliyoruz! Lütfen:

1. Fork yapın
2. Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Commit yapın (`git commit -m 'Add amazing feature'`)
4. Push yapın (`git push origin feature/amazing-feature`)
5. Pull Request açın

## 📝 Lisans

Bu proje MIT lisansı altında yayınlanmıştır. Detaylar için `LICENSE` dosyasını inceleyin.

## 🔗 Bağlantılar

- [Home Assistant](https://www.home-assistant.io/)
- [HACS](https://hacs.xyz/)
- [TIS Protocol Documentation](./docs/TIS_PROTOCOL.md)
- [Issue Tracker](https://github.com/your-username/tis-home-automation/issues)

## 📞 Destek

Sorunlarınız için:
1. [GitHub Issues](https://github.com/your-username/tis-home-automation/issues)
2. [Home Assistant Community](https://community.home-assistant.io/)
3. [Discord Server](https://discord.gg/home-assistant)

---

**⭐ Bu proje size yardımcı olduysa, GitHub'da yıldız vermeyi unutmayın!**
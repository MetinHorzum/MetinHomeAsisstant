# TIS Home Automation

[![GitHub Release][releases-shield]][releases]
[![License][license-shield]](LICENSE)
[![hacs][hacsbadge]][hacs]

_TIS akıllı ev cihazları için kapsamlı Home Assistant entegrasyonu_

**Bu entegrasyon, TIS protokolünü kullanarak 150+ farklı akıllı ev cihazını Home Assistant ile entegre etmenizi sağlar.**

## Özellikler

- 🏠 **150+ Cihaz Desteği**: Anahtar, dimmer, klima, sensör ve daha fazlası
- 📡 **Çift İletişim**: UDP ağ ve RS485 seri haberleşme
- 🔍 **Otomatik Keşif**: SMARTCLOUD protokolü ile cihaz tespiti
- 🌐 **Çoklu Dil**: Türkçe ve İngilizce arayüz
- ⚡ **Asenkron**: Non-blocking, yüksek performanslı
- 🛠 **Gelişmiş Servisler**: Ham komut gönderme, cihaz yönetimi

## Desteklenen Cihaz Kategorileri

### 💡 Aydınlatma
- **Anahtarlar**: 1-4 gang anahtarlar
- **Dimmerlar**: 1-2 gang parlaklık kontrolü  
- **Sahne Kontrolleri**: Çoklu sahne yönetimi
- **Perde Kontrolleri**: Otomatik perde sistemleri

### 🌡️ İklim Kontrolü
- **Klima Kontrolleri**: Tam AC yönetimi
- **Termostatlar**: Sıcaklık kontrolü
- **Yerden Isıtma**: Radyant ısıtma sistemleri
- **Fan Kontrolleri**: Hava sirkülasyon kontrolü

### 📊 Sensörler
- **Çevre Sensörleri**: Sıcaklık, nem, ışık
- **Hareket Sensörleri**: PIR algılayıcılar
- **Kapı/Pencere Sensörleri**: Manyetik kontaklar
- **Sağlık Sensörleri**: 6-in-1 hava kalitesi monitörleri
- **Güvenlik Sensörleri**: Duman, gaz algılayıcıları

### 🔒 Güvenlik
- **Akıllı Kilitler**: Elektronik kilit kontrolü
- **Alarm Panelleri**: Güvenlik sistem yönetimi
- **Kamera Kontrolleri**: Güvenlik kamerası entegrasyonu

## Kurulum

### HACS ile Kurulum (Önerilen)

1. HACS'i açın
2. **Integrations** sekmesine gidin
3. **Explore & Download Repositories**'e tıklayın
4. "TIS Home Automation" arayın
5. **Download** butonuna tıklayın
6. Home Assistant'ı yeniden başlatın
7. **Ayarlar** → **Cihazlar ve Servisler** → **Entegrasyon Ekle**
8. "TIS Home Automation" arayın ve kurun

### Manuel Kurulum

1. Bu repository'yi indirin
2. `custom_components/tis_home_automation` klasörünü Home Assistant'ın `custom_components` dizinine kopyalayın
3. `tis_protocol` kütüphanesini de aynı dizine kopyalayın
4. Home Assistant'ı yeniden başlatın

## Yapılandırma

Entegrasyonu kurduktan sonra:

1. **Ayarlar** → **Cihazlar ve Servisler** → **Entegrasyon Ekle**
2. **TIS Home Automation**'ı seçin
3. İletişim türünü seçin:
   - **UDP**: Ağ üzerinden haberleşme (önerilen)
   - **RS485**: Seri port üzerinden doğrudan bağlantı
4. Bağlantı ayarlarını yapın
5. Cihaz keşfini başlatın

## İletişim Seçenekleri

### UDP Ağ İletişimi
```
IP Adresi: 192.168.1.100 (Home Assistant sunucunuz)
Port: 6000 (TIS varsayılanı)
```

### RS485 Seri İletişim
```
Seri Port: /dev/ttyUSB0 (Linux) veya COM3 (Windows)
Baud Hızı: 9600 (varsayılan)
```

## Servisler

Bu entegrasyon özel servisler sunar:

- `tis_home_automation.discover_devices` - Yeni cihaz keşfi
- `tis_home_automation.send_raw_command` - Ham TIS komut gönderme
- `tis_home_automation.ac_control` - Gelişmiş klima kontrolü
- `tis_home_automation.lighting_control` - Gelişmiş aydınlatma kontrolü

## Örnek Kullanım

### Otomatik Aydınlatma
```yaml
automation:
  - alias: "Hareket Algılandığında Işığı Aç"
    trigger:
      platform: state
      entity_id: binary_sensor.tis_motion_01
      to: "on"
    action:
      service: switch.turn_on
      entity_id: switch.tis_switch_01
```

### İklim Kontrolü
```yaml
automation:
  - alias: "Sıcaklık Yüksek - Klimayı Aç"
    trigger:
      platform: numeric_state
      entity_id: sensor.tis_temperature_02
      above: 28
    action:
      service: tis_home_automation.ac_control
      data:
        device_id: "03FE"
        power: "on"
        mode: "cool"
        temperature: 24
```

## Sorun Giderme

**Cihazlar bulunamıyor?**
- IP adresi ve port ayarlarını kontrol edin
- Güvenlik duvarı kurallarını kontrol edin
- TIS cihazlarının aynı ağda olduğunu doğrulayın

**Seri port bağlantı hatası?**
- Port adresini kontrol edin: `ls /dev/tty*`
- Kullanıcı izinlerini kontrol edin: `sudo usermod -a -G dialout homeassistant`
- RS485 adaptörünün düzgün takıldığını kontrol edin

**Debug modunu etkinleştirin:**
```yaml
logger:
  logs:
    custom_components.tis_home_automation: debug
    tis_protocol: debug
```

## Destek

- [GitHub Issues](https://github.com/your-username/tis-home-automation/issues)
- [Home Assistant Community](https://community.home-assistant.io/)
- [Türkçe Dokümantasyon](README.md)

## Katkı

Bu projeye katkıda bulunmak isterseniz:

1. Repository'yi fork edin
2. Feature branch oluşturun
3. Değişikliklerinizi commit edin
4. Pull request gönderin

## Lisans

Bu proje MIT lisansı altında yayınlanmıştır.

---

Bu entegrasyonu beğendiyseniz, GitHub'da ⭐ vermeyi unutmayın!

[releases-shield]: https://img.shields.io/github/release/your-username/tis-home-automation.svg?style=for-the-badge
[releases]: https://github.com/your-username/tis-home-automation/releases
[license-shield]: https://img.shields.io/github/license/your-username/tis-home-automation.svg?style=for-the-badge
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
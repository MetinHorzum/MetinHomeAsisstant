# TIS Control - Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

Türk akıllı ev protokolü TIS (Total Integration System) için geliştirilmiş Home Assistant custom integration'ı.

## ✨ Özellikler

### Desteklenen Cihaz Tipleri
- **💡 Işıklandırma**: Dimmer, RGB, RGBW LED şeritleri
- **🔌 Anahtarlar**: Röle kontrollü anahtarlar
- **🌡️ İklim Kontrol**: Klima ve yer ısıtması sistemleri
- **📊 Sensörler**: Analog, dijital, sıcaklık, enerji sensörleri
- **🏥 Sağlık Sensörleri**: Hava kalitesi, CO2, TVOC, gürültü
- **🪟 Perdeler**: Motor kontrollü perde sistemleri
- **🚨 Güvenlik**: Motion detektör ve güvenlik sensörleri

### Teknik Özellikler
- UDP protokolü üzerinden iletişim
- Gerçek zamanlı durum güncellemeleri
- Otomatik cihaz keşfi
- HACS desteği
- Türkçe kullanıcı arayüzü

## 🚀 Kurulum

### HACS ile Kurulum (Önerilen)

1. Home Assistant'ta HACS'i açın
2. **Integrations** sekmesine gidin
3. Sağ üst köşedeki **⋮** menüsüne tıklayın
4. **Custom repositories** seçeneğini seçin
5. Bu repository'nin GitHub URL'ini ekleyin
6. Category olarak **Integration** seçin
7. **ADD** butonuna tıklayın
8. **TIS Control** integration'ını bulun ve kurun
9. Home Assistant'ı yeniden başlatın

### Manuel Kurulum

1. Bu repository'yi indirin
2. `custom_components` klasörünü Home Assistant config dizininize kopyalayın
3. Home Assistant'ı yeniden başlatın

## ⚙️ Konfigürasyon

1. Home Assistant'ta **Settings** > **Devices & Services** bölümüne gidin
2. **ADD INTEGRATION** butonuna tıklayın
3. **TIS Control** integration'ını arayın ve seçin
4. UDP port numarasını girin (varsayılan: 4001)
5. **SUBMIT** butonuna tıklayın

## 🔧 Desteklenen Cihazlar

| Cihaz Kodu | Cihaz Adı | Açıklama |
|------------|-----------|----------|
| `0x1B, 0xBA` | RCU-8OUT-8IN | 8 Çıkış 8 Giriş Kontrol Ünitesi |
| `0x0B, 0xE9` | SEC-SM | Güvenlik Modülü |
| `0x80, 0x58` | IP-COM-PORT | IP İletişim Portu |
| `0x01, 0xA8` | RLY-4CH-10 | 4 Kanal 10A Röle |
| `0x23, 0x32` | LUNA-TFT-43 | Dokunmatik Ekran Panel |
| `0x02, 0x5A` | DIM-2CH-6A | 2 Kanal 6A Dimmer |
| `0x02, 0x58` | DIM-6CH-2A | 6 Kanal 2A Dimmer |

## 🏠 Örnek Kullanım

```yaml
# automation.yaml
- alias: "Akşam Aydınlatması"
  trigger:
    - platform: sun
      event: sunset
  action:
    - service: light.turn_on
      target:
        entity_id: light.salon_dimmer
      data:
        brightness_pct: 80

- alias: "Klima Otomasyonu"
  trigger:
    - platform: numeric_state
      entity_id: sensor.salon_sicaklik
      above: 25
  action:
    - service: climate.set_hvac_mode
      target:
        entity_id: climate.salon_klima
      data:
        hvac_mode: cool
```

## 🐛 Sorun Giderme

### Yaygın Sorunlar

**1. Cihazlar görünmüyor**
- UDP port numarasının doğru olduğunu kontrol edin
- Network bağlantısını kontrol edin
- Home Assistant loglarını inceleyin

**2. Cihaz durumu güncellenmiyor**
- TIS gateway'in çalıştığından emin olun
- Network trafiğini kontrol edin
- Integration'ı yeniden yapılandırın

**3. Komutlar çalışmıyor**
- Cihaz adreslerinin doğru olduğunu kontrol edin
- UDP paket formatını kontrol edin

### Log Kontrolü

```yaml
# configuration.yaml
logger:
  default: info
  logs:
    custom_components.tis_control: debug
```

## 🤝 Katkıda Bulunma

1. Bu repository'yi fork edin
2. Yeni bir branch oluşturun (`git checkout -b feature/yeni-ozellik`)
3. Değişikliklerinizi commit edin (`git commit -am 'Yeni özellik eklendi'`)
4. Branch'inizi push edin (`git push origin feature/yeni-ozellik`)
5. Pull Request oluşturun

## 📝 Lisans

Bu proje MIT lisansı altında lisanslanmıştır. Detaylar için [LICENSE](LICENSE) dosyasını inceleyin.

## 🙏 Teşekkürler

- Home Assistant topluluğuna
- TIS protokol geliştirici ekibine
- HACS projesine

## 📞 İletişim

- GitHub Issues: Bu repository'de sorun bildirebilirsiniz
- Geliştirici: Repository sahibi ile iletişime geçebilirsiniz

---

**Not**: Bu integration henüz beta aşamasındadır. Üretim ortamında kullanırken dikkatli olun.
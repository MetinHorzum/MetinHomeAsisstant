# TIS Control - Sorun Giderme Rehberi

## ❌ "Invalid handler specified" Hatası

Bu hatayı aldıysanız, şu adımları takip edin:

### 1. Home Assistant'ı Yeniden Başlatın
```bash
# Home Assistant'ı tamamen yeniden başlatın
sudo systemctl restart homeassistant
```

### 2. Dosya İzinlerini Kontrol Edin
```bash
# Custom components klasör izinlerini kontrol edin
ls -la /config/custom_components/tis_control/
```

### 3. Log Dosyalarını İnceleyin
```yaml
# configuration.yaml dosyasına ekleyin
logger:
  default: warning
  logs:
    custom_components.tis_control: debug
```

### 4. TISControlProtocol Kütüphanesini Kurun
```bash
# Home Assistant container içinde
pip install TISControlProtocol==1.0.5
```

## 📝 Test Adımları

### 1. Manuel Test
Integration'ı test etmek için:

1. **Developer Tools** > **Services** bölümüne gidin
2. `homeassistant.reload_config_entry` servisini çalıştırın
3. Logs bölümünde hataları kontrol edin

### 2. Konfigürasyon Dosyası Testi
```yaml
# configuration.yaml - Test konfigürasyonu
tis_control:
  port: 4001
```

## 🔧 Yaygın Sorunlar ve Çözümleri

### Problem 1: Integration Görünmüyor
**Çözüm:**
- `custom_components/tis_control/` klasörünün doğru yerde olduğunu kontrol edin
- `manifest.json` dosyasının mevcut olduğunu kontrol edin
- Home Assistant'ı yeniden başlatın

### Problem 2: "TISControlProtocol not found"
**Çözüm:**
```bash
# Home Assistant venv'inde kütüphaneyi kurun
pip install TISControlProtocol aiofiles ruamel.yaml psutil
```

### Problem 3: UDP Bağlantı Sorunu
**Çözüm:**
- Port 4001'in açık olduğunu kontrol edin
- Firewall ayarlarını kontrol edin
- Network bağlantısını test edin

## 🛠️ Debug Komutları

### 1. Integration Status
```python
# Developer Tools > Template
{% for domain in states | map(attribute='domain') | unique | list %}
  {{ domain }}
{% endfor %}
```

### 2. Port Testi
```bash
# Port dinleme kontrolü
netstat -tulpn | grep 4001
```

### 3. Import Testi
```python
# Python console'da test
try:
    from TISControlProtocol.api import TISApi
    print("TISControlProtocol başarıyla import edildi")
except ImportError as e:
    print(f"Import hatası: {e}")
```

## 📋 Kurulum Kontrol Listesi

- [ ] `custom_components/tis_control/` klasörü mevcut
- [ ] Tüm Python dosyaları (.py) mevcut
- [ ] `manifest.json` dosyası doğru formatta
- [ ] `TISControlProtocol` kütüphanesi kurulu
- [ ] Home Assistant yeniden başlatıldı
- [ ] Port 4001 erişilebilir
- [ ] Network bağlantısı aktif

## 🆘 Yardım Alma

### 1. Log Dosyası Paylaşımı
```bash
# Relevant logs'u kopyalayın
grep -i "tis_control" /config/home-assistant.log
```

### 2. Sistem Bilgileri
- Home Assistant versiyon: `Settings > System > Repairs`
- Python versiyon: Developer Tools'da kontrol
- TIS cihaz modeli ve firmware versiyon

### 3. GitHub Issues
- Detaylı hata mesajı
- Tam log dosyası
- Sistem bilgileri
- Denediğiniz çözümler

## 💡 İpuçları

1. **İlk Kurulum**: Integration'ı ilk kez kuruyorsanız, önce küçük bir test ile başlayın
2. **Ağ Ayarları**: TIS cihazlarınızın aynı ağda olduğundan emin olun
3. **Backup**: Kurulumdan önce Home Assistant backup'ı alın
4. **Güncelleme**: Integration'ı güncelledikten sonra Home Assistant'ı yeniden başlatın

## 🔄 Temiz Kurulum

Eğer sorunlar devam ederse, temiz kurulum yapın:

```bash
# 1. Integration'ı kaldırın
rm -rf /config/custom_components/tis_control/

# 2. Home Assistant'ı yeniden başlatın
sudo systemctl restart homeassistant

# 3. Integration'ı yeniden kurun
# GitHub'dan tekrar indirin ve kurulum adımlarını takip edin
# TIS Control - Kurulum Rehberi

## 📋 Sistem Gereksinimleri

- Home Assistant 2024.1.0 veya üzeri
- Python 3.11+
- Network bağlantısı (TIS cihazları ile aynı ağ)

## 🚀 Adım Adım Kurulum

### 1. Integration Kurulumu

#### HACS ile (Önerilen)
1. HACS'i açın > **Integrations**
2. **⋮** > **Custom repositories**
3. Repository URL'inizi ekleyin
4. **TIS Control**'u bulun ve kurun

#### Manuel Kurulum
1. Bu dosyaları indirin
2. `/config/custom_components/tis_control/` klasörüne kopyalayın

### 2. TIS Kütüphanesi Kurulumu

#### Seçenek A: Home Assistant Container/Docker
```bash
# Container'a girin
docker exec -it homeassistant bash

# Kütüphaneyi kurun
pip install TISControlProtocol==1.0.5 aiofiles ruamel.yaml psutil

# Container'ı yeniden başlatın
exit
docker restart homeassistant
```

#### Seçenek B: Home Assistant OS (SSH)
1. **Settings** > **Add-ons** > **Add-on Store**
2. **Terminal & SSH** add-on'unu kurun
3. SSH ile bağlanın:

```bash
# SSH'la bağlandıktan sonra
apk add --no-cache gcc musl-dev python3-dev
pip install TISControlProtocol==1.0.5 aiofiles ruamel.yaml psutil
```

#### Seçenek C: Home Assistant Core (Python venv)
```bash
# Home Assistant kullanıcısına geçin
sudo -u homeassistant -H -s

# Virtual environment'ı aktifleştirin
source /srv/homeassistant/bin/activate

# Kütüphaneyi kurun
pip install TISControlProtocol==1.0.5 aiofiles ruamel.yaml psutil

# Home Assistant'ı yeniden başlatın
sudo systemctl restart homeassistant
```

### 3. Integration Ekleme

1. **Settings** > **Devices & Services**
2. **+ ADD INTEGRATION**
3. **TIS Control** arayın
4. **UDP Port** girin (varsayılan: 4001)
5. **Submit** tıklayın

## 🔧 Kütüphane Kurulum Kontrolü

Integration eklendikten sonra logları kontrol edin:

```yaml
# configuration.yaml
logger:
  default: warning
  logs:
    custom_components.tis_control: info
```

**Başarılı kurulum mesajı:**
```
TISControlProtocol library loaded successfully
```

**Mock mode mesajı (kütüphane yok):**
```
Running in mock mode - TISControlProtocol library not found
```

## 🐛 Sorun Giderme

### Problem: "TISControlProtocol library not installed"
**Çözüm:**
1. Yukarıdaki kurulum adımlarını tekrarlayın
2. Home Assistant'ı tamamen yeniden başlatın
3. Python path'ini kontrol edin

### Problem: "pip: command not found"
**Çözüm (Home Assistant OS):**
```bash
# Python ve pip'i kurun
apk add --no-cache python3 py3-pip python3-dev gcc musl-dev
```

### Problem: Import hatası devam ediyor
**Çözüm:**
```bash
# Manuel kontrol
python3 -c "import TISControlProtocol; print('OK')"

# Eğer hata alırsanız:
pip uninstall TISControlProtocol
pip install --no-cache-dir TISControlProtocol==1.0.5
```

## 📦 Alternatif Kurulum (requirements.txt)

Eğer otomatik kurulum istiyorsanız, Home Assistant config dizininizde:

```bash
# requirements.txt oluşturun
echo "TISControlProtocol==1.0.5" >> /config/requirements.txt
echo "aiofiles==24.1.0" >> /config/requirements.txt
echo "ruamel.yaml==0.18.10" >> /config/requirements.txt
echo "psutil==7.0.0" >> /config/requirements.txt
```

## ⚡ Hızlı Test

Kurulumdan sonra Python console'da test edin:

```python
# Home Assistant Python console
try:
    from TISControlProtocol.api import TISApi
    print("✅ TIS kütüphanesi başarıyla kuruldu!")
except ImportError as e:
    print(f"❌ Kurulum hatası: {e}")
```

## 🔄 Mock Mode'dan Çıkış

Integration mock mode'da çalışıyorsa:

1. Kütüphaneyi kurun (yukarıdaki adımlar)
2. **Settings** > **Devices & Services**
3. **TIS Control** > **⋮** > **Reload**
4. Logları kontrol edin

## 📞 Yardım

- **Discord**: Home Assistant Türkiye
- **GitHub Issues**: Repository'de sorun bildirin
- **Log Dosyası**: Her zaman `/config/home-assistant.log`'u ekleyin

## ✅ Kurulum Tamamlandı

Başarılı kurulumda şunları görmelisiniz:
- **Devices & Services**'te TIS Control
- **Developer Tools** > **States**'te tis_control entityleri
- Logda "TISControlProtocol library loaded successfully"
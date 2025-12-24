# TIS Home Automation - Deployment Rehberi

## 🏠 Home Assistant'a Kurulum

### Manuel Kurulum (Önerilen Test İçin)

Home Assistant'ınızın `config` klasöründe aşağıdaki yapıyı oluşturun:

```
config/
├── custom_components/
│   └── tis_home_automation/          # Bu klasörü kopyalayın
│       ├── __init__.py
│       ├── binary_sensor.py
│       ├── climate.py
│       ├── config_flow.py
│       ├── const.py
│       ├── coordinator.py
│       ├── entity.py
│       ├── light.py
│       ├── manifest.json
│       ├── sensor.py
│       ├── services.py
│       ├── strings.json
│       └── switch.py
├── deps/
│   └── lib/
│       └── python3.11/
│           └── site-packages/
│               └── tis_protocol/      # Bu klasörü kopyalayın
│                   ├── __init__.py
│                   ├── communication.py
│                   ├── core.py
│                   └── helpers.py
└── translations/
    └── tr.json                       # Bu dosyayı kopyalayın
```

### Adım Adım Kurulum

**1. Dosyaları Home Assistant'a Kopyalayın**

Windows için (PowerShell):
```powershell
# Home Assistant config klasörüne gidin
cd "C:\path\to\homeassistant\config"

# custom_components klasörünü oluşturun (yoksa)
mkdir custom_components -ea 0

# TIS integration'ı kopyalayın
cp -Recurse "C:\Users\Meth\Desktop\TIS Automation\custom_components\tis_home_automation" ".\custom_components\"

# deps klasörünü oluşturun
mkdir deps\lib\python3.11\site-packages -ea 0

# TIS protocol library'yi kopyalayın
cp -Recurse "C:\Users\Meth\Desktop\TIS Automation\tis_protocol" ".\deps\lib\python3.11\site-packages\"

# Translations klasörünü oluşturun
mkdir translations -ea 0

# Türkçe çeviri dosyasını kopyalayın
cp "C:\Users\Meth\Desktop\TIS Automation\translations\tr.json" ".\translations\"
```

Linux/macOS için:
```bash
# Home Assistant config klasörüne gidin
cd /config  # veya /usr/share/hassio/homeassistant

# Dosyaları kopyalayın
cp -r /path/to/TIS\ Automation/custom_components/tis_home_automation ./custom_components/
mkdir -p deps/lib/python3.11/site-packages
cp -r /path/to/TIS\ Automation/tis_protocol ./deps/lib/python3.11/site-packages/
mkdir -p translations
cp /path/to/TIS\ Automation/translations/tr.json ./translations/
```

**2. Home Assistant'ı Yeniden Başlatın**

**3. Integration'ı Kurun**
1. **Ayarlar** → **Cihazlar ve Servisler**
2. **Entegrasyon Ekle** butonuna tıklayın
3. "TIS Home Automation" arayın
4. Kurulum sihirbazını takip edin

## 📦 GitHub Repository Oluşturma

### GitHub'a Yüklenecek Dosyalar

```
repository-root/
├── custom_components/
│   └── tis_home_automation/          # ✅ Gerekli
│       └── [tüm dosyalar]
├── tis_protocol/                     # ✅ Gerekli
│   └── [tüm dosyalar]
├── translations/                     # ✅ Gerekli
│   └── tr.json
├── tests/                           # ✅ İsteğe bağlı (geliştiriciler için)
│   └── [test dosyları]
├── hacs.json                        # ✅ HACS için gerekli
├── info.md                          # ✅ HACS için gerekli
├── README.md                        # ✅ Gerekli
├── LICENSE                          # ✅ Gerekli
├── PRODUCTION_READINESS.md          # ✅ Geliştiriciler için
└── requirements-dev.txt             # ❌ GitHub'a eklemeyin
```

### GitHub Repository Kurulum Komutları

```bash
# Repository oluşturun
git init
git branch -M main

# .gitignore oluşturun
echo "# Development files
requirements-dev.txt
__pycache__/
*.pyc
*.pyo
.pytest_cache/
.coverage
.vscode/
.idea/

# OS files
.DS_Store
Thumbs.db" > .gitignore

# Dosyaları ekleyin
git add custom_components/
git add tis_protocol/
git add translations/
git add tests/
git add *.json
git add *.md
git add LICENSE

# İlk commit
git commit -m "Initial release: TIS Home Automation integration v1.0.0"

# GitHub remote ekleyin
git remote add origin https://github.com/yourusername/tis-home-automation.git

# Push edin
git push -u origin main

# Release tag'i oluşturun
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0
```

## 🏪 HACS Store'a Ekleme

### HACS Onaylı Repository Olmak İçin

1. **Repository Requirements**:
   - ✅ [`hacs.json`](hacs.json) dosyası mevcut
   - ✅ [`info.md`](info.md) dosyası mevcut  
   - ✅ [`README.md`](README.md) dokümantasyon mevcut
   - ✅ [`LICENSE`](LICENSE) dosyası mevcut
   - ✅ GitHub releases ile versioning
   - ✅ Proper manifest.json dosyası

2. **HACS Submission**:
   - [HACS Community Store](https://github.com/hacs/integration) repository'sine PR gönderin
   - [`hacs.json`](hacs.json) dosyanızı brands repository'ye ekleyin

### Kullanıcılar İçin HACS Kurulumu

1. HACS'da **Custom Repositories** bölümüne gidin
2. Repository URL'ini ekleyin: `https://github.com/yourusername/tis-home-automation`
3. Category: **Integration** seçin
4. **Add** butonuna tıklayın
5. Repository listesinde bulup **Download** edin

## 🔧 Geliştirici Kurulumu

Geliştirme ortamı kurmak isteyen geliştiriciler için:

```bash
# Repository'yi klonlayın
git clone https://github.com/yourusername/tis-home-automation.git
cd tis-home-automation

# Virtual environment oluşturun
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate     # Windows

# Development dependencies kurun
pip install homeassistant pytest pytest-asyncio

# Tests çalıştırın
pytest tests/
```

## ✅ Kurulum Doğrulama

Kurulum sonrası kontrol listesi:

- [ ] Home Assistant loglarında TIS import hataları yok
- [ ] **Ayarlar** → **Cihazlar ve Servisler**'de "TIS Home Automation" görünüyor
- [ ] Integration kurulum wizard'ı açılıyor
- [ ] Cihaz keşfi çalışıyor (test cihazı ile)
- [ ] Entity'ler Home Assistant dashboard'unda görünüyor
- [ ] **Geliştirici Araçları** → **Servisler**'de TIS servisleri listeleniyor

## 🐛 Sorun Giderme

**Import hatalarında:**
```bash
# Home Assistant loglarını kontrol edin
tail -f /config/home-assistant.log | grep tis

# Custom components klasör yapısını kontrol edin
ls -la /config/custom_components/tis_home_automation/
```

**Cihaz bulunamadığında:**
```yaml
# configuration.yaml'a debug logging ekleyin
logger:
  logs:
    custom_components.tis_home_automation: debug
    tis_protocol: debug
```

Bu rehber ile TIS Home Automation integration'ınızı başarıyla deploy edebilirsiniz!
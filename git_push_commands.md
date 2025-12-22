# GitHub Push Komutları

Bu dosyadaki komutları sırayla çalıştırarak TIS Control integration'ınızı GitHub'a yükleyebilirsiniz.

## 1. Git Repository Başlatma

```bash
cd "C:\Users\Meth\Desktop\Github\MetinHomeAsisstant"
git init
```

## 2. Remote Repository Ekleme

**ÖNEMLI**: Aşağıdaki URL'yi kendi GitHub repository URL'inizle değiştirin!

```bash
git remote add origin https://github.com/KULLANICI-ADINIZ/REPO-ADINIZ.git
```

Örnek:
```bash
git remote add origin https://github.com/kullanici/tis-home-assistant.git
```

## 3. Dosyaları Stage'e Ekleme

```bash
git add .
```

## 4. İlk Commit

```bash
git commit -m "Initial commit: TIS Control Home Assistant Integration

- Complete TIS integration with 20+ device types
- HACS compatible structure
- Support for lights, switches, climate, sensors
- Turkish smart home protocol integration
- Laravel device scanner interface
- Automatic device discovery
- Professional documentation"
```

## 5. GitHub'a Push

```bash
git push -u origin main
```

## 6. HACS İçin Release Oluşturma

GitHub web arayüzünde:

1. Repository'nize gidin
2. **Releases** sekmesine tıklayın
3. **Create a new release** butonuna tıklayın
4. Tag version: `v1.0.0`
5. Release title: `TIS Control v1.0.0 - Initial Release`
6. Release notes:

```markdown
## 🚀 TIS Control v1.0.0

İlk stabil sürüm! Türk akıllı ev protokolü TIS için tam özellikli Home Assistant integration'ı.

### ✨ Özellikler
- 20+ cihaz tipi desteği
- Işıklar: Dimmer, RGB, RGBW
- Anahtarlar: Röle kontrollü
- İklim: Klima ve yer ısıtması
- Sensörler: Analog, digital, enerji
- Sağlık sensörleri: Hava kalitesi
- Perdeler: Motor kontrollü
- Güvenlik: Motion detector

### 🔧 Kurulum
1. HACS'te custom repository olarak ekleyin
2. Integration'ı kurun
3. UDP port'u yapılandırın (varsayılan: 4001)

### 📊 Teknik Detaylar
- UDP protokol desteği
- Gerçek zamanlı güncellemeler
- Otomatik cihaz keşfi
- Laravel web arayüzü
- Profesyonel dokümantasyon
```

## 7. HACS Custom Repository Olarak Ekleme

Kullanıcılar şu adımları takip edecek:

1. HACS > Integrations
2. ⋮ menü > Custom repositories
3. Repository URL: `https://github.com/KULLANICI-ADINIZ/REPO-ADINIZ` 
4. Category: Integration
5. ADD butonuna tıkla
6. TIS Control'u bul ve kur

## 8. Manifest Dosyasını Güncelleme

`custom_components/tis_control/manifest.json` dosyasındaki documentation URL'ini kendi repository'nizle güncelleyin:

```json
"documentation": "https://github.com/KULLANICI-ADINIZ/REPO-ADINIZ"
```

## ⚠️ Önemli Notlar

- Repository URL'lerini kendi bilgilerinizle değiştirmeyi unutmayın
- GitHub repository'nizi public yapın ki HACS erişebilsin
- İlk release'i oluşturmadan HACS'te görünmez
- README.md dosyasına da kendi bilgilerinizi ekleyebilirsiniz
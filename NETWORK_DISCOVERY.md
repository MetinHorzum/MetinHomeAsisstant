# 🔍 TIS Cihaz Keşfi ve Ağ Taraması Rehberi

TIS cihazlarınızı keşfetmek için **2 farklı yöntem** mevcuttur:

## 🌐 Yöntem 1: Laravel Web Arayüzü (Önerilen)

### Avantajları:
- ✅ Kolay kullanım 
- ✅ Görsel arayüz
- ✅ Gerçek zamanlı tarama
- ✅ Otomatik cihaz ekleme
- ✅ CIDR desteği

### Kurulum:
```bash
# Laravel sunucusunu başlatın
cd tis-addon-main/laravel/laravel
php artisan serve

# Tarayıcıda açın
http://127.0.0.1:8000/device-scanner
```

### Kullanım:
1. **Network Range** girin (örn: `192.168.1.0/24`)
2. **Start Scan** butonuna tıklayın
3. Bulunan TIS cihazları listelenir
4. **Add to System** ile otomatik ekleyin

---

## 🏠 Yöntem 2: Home Assistant Integration Discovery

### Avantajları:
- ✅ Home Assistant içinde çalışır
- ✅ Bulunan cihazları doğrudan integration'a ekler
- ✅ Gelişmiş filtreleme
- ✅ Cihaz seçimi

### Kullanım:
1. **Settings** > **Devices & Services**
2. **+ ADD INTEGRATION**
3. **TIS Control** seçin
4. **Port**: 4001 girin
5. **Network Range**: `192.168.1.0/24` girin
6. **Scan Timeout**: 3 saniye
7. Bulunan cihazları seçin

---

## 🔧 TIS Cihaz Discovery Protokolü

### Tarama Algoritması:
```python
# IP aralığı: 192.168.1.1 - 192.168.1.254
# Port'lar: 4001, 4002, 8080, 9090
# Discovery paketi: 0x55 0xAA 0x00 0x01 0x00 0x00 0x01
```

### TIS Cihaz Tanıma:
- TCP bağlantısı kurulur
- Discovery paketi gönderilir
- Yanıt beklemesi: 3 saniye
- Geçerli yanıt alınırsa TIS cihazı olarak kaydedilir

---

## 📊 Örnek Tarama Sonuçları

### Laravel Web Arayüzü:
```json
{
  "found_devices": [
    {
      "ip": "192.168.1.100",
      "port": 4001,
      "device_type": "RCU-8OUT-8IN",
      "device_id": "1BBA",
      "status": "online",
      "channels": [
        {"1": "light_dimmer"},
        {"2": "switch_relay"}
      ]
    }
  ]
}
```

### Home Assistant Discovery:
```
🔍 TIS Cihaz Taraması Başlıyor: 192.168.1.0/24
✅ 2 TIS cihazı bulundu!
  - TIS Device - 192.168.1.100:4001
  - TIS Device - 192.168.1.150:4001
```

---

## 🎯 Hangi Yöntemi Seçmeli?

### Laravel Web Arayüzü Şu Durumlarda:
- İlk kurulum yapıyorsunuz
- Cihaz detaylarını görmek istiyorsunuz  
- Toplu cihaz yapılandırması gerekiyor
- Network üzerinde test yapmak istiyorsunuz

### Home Assistant Discovery Şu Durumlarda:
- Home Assistant içinde kalarak çalışmak istiyorsunuz
- Minimal kurulum istiyorsunuz
- Sadece gerekli cihazları seçmek istiyorsunuz

---

## 🚨 Yaygın Sorunlar ve Çözümleri

### Problem: "Cihaz bulunamadı"
**Çözümler:**
- Ağ aralığını kontrol edin (`192.168.1.0/24`)
- TIS cihazlarının aynı ağda olduğunu doğrulayın
- Timeout süresini artırın (5-10 saniye)
- Firewall ayarlarını kontrol edin

### Problem: "Bağlantı reddedildi"
**Çözümler:**
- TIS cihazı IP adresini ping ile test edin
- Port numarasını kontrol edin (4001, 4002, 8080)
- TIS cihazının çalıştığından emin olun

### Problem: "Yanlış cihaz tipi"
**Çözümler:**
- Device ID'yi manuel kontrol edin
- Farklı port'ları deneyin
- TIS protokol versiyonunu kontrol edin

---

## 📝 Manual Cihaz Ekleme

Eğer otomatik tarama çalışmazsa manuel ekleme:

```yaml
# Home Assistant configuration.yaml
tis_control:
  devices:
    - name: "Salon Lambası"
      ip: "192.168.1.100"
      port: 4001
      device_id: "1BBA"
      type: "dimmer"
      channel: 1
```

---

## 🔍 Network Debugging

### Port Tarama:
```bash
# Manuel port kontrolü
nmap -p 4001,4002,8080,9090 192.168.1.100

# TIS protokol testi
telnet 192.168.1.100 4001
```

### Paket İzleme:
```bash
# Wireshark ile TIS paketlerini izleyin
# Filter: tcp.port == 4001
```

---

## 💡 İpuçları

1. **İlk kurulumda Laravel web arayüzünü kullanın** - Daha detaylı bilgi verir
2. **Ağ tarama süresini optimize edin** - Büyük ağlarda timeout'u artırın  
3. **Cihaz türlerini kontrol edin** - Her TIS cihazının farklı özellikleri vardır
4. **Backup yapın** - Bulunan cihaz listesini kaydedin
5. **Log'ları takip edin** - Sorun giderme için faydalı

Bu rehberle gerçek TIS cihazlarınızı kolayca keşfedebilir ve Home Assistant'a entegre edebilirsiniz! 🎉
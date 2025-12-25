# TIS Home Assistant Custom Integration (SmartCloud UDP)

Bu paket, TIS IP gateway'in (ör. 192.168.1.200) **UDP 6000** üzerinden yaptığı **0x000E Discovery** yayınını gönderir ve
**0x000F Discovery Response** paketlerini dinleyerek ağdaki TIS cihazlarını yakalar.

## Kurulum

1. Zip içindeki `custom_components/tis` klasörünü Home Assistant config klasörünüze kopyalayın:

```
/config/custom_components/tis
```

2. Home Assistant'ı yeniden başlatın.
3. HA UI: **Ayarlar → Cihazlar ve Hizmetler → Entegrasyon Ekle → "TIS Home (SmartCloud UDP)"** (adı "TIS Home" olarak görünebilir)
4. Host: `192.168.1.200`, Port: `6000`

## Şu an ne yapıyor?

- UDP 6000 dinler.
- Kurulumda otomatik 1 kez discovery yapar.
- `sensor.tis_discovered_devices` ve `sensor.tis_seconds_since_last_packet` şeklinde iki debug sensörü ekler.

## Sonraki adım

Discovery sonrası gelen cihazların `op_code`'larına göre gerçek sensör entity'leri (sıcaklık/nem/PIR vs.) eklenebilir.

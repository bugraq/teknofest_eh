# TEKNOFEST EH — Elektronik Harp Sistemi

SDR üzerinden canlı IQ verisi alıp ONNX modeliyle modülasyon tanıma (ED) yapan,
yön bulma / karıştırma / aldatma panellerini içeren PyQt6 arayüzü.

---

## 1. Kurulum

```bash
git clone https://github.com/bugraq/teknofest_eh.git
```

```bash
cd teknofest_eh && python -m venv .venv
```

Sanal ortamı aktif et:

```bash
.venv\Scripts\activate
```

(Linux/macOS: `source .venv/bin/activate`)

```bash
pip install -r requirements.txt
```

Python 3.10+ önerilir.

## 2. Model

ONNX modeli repoya dahildir, ayrıca indirmene gerek yok:

- `data/model.onnx` — model grafiği
- `data/model.onnx.data` — ağırlıklar (~16 MB, **ikisi de aynı klasörde durmalı**)

Model bulunamazsa uygulama çökmez, `[AI ENGINE UYARISI]` basıp **simülasyon
(Fake AI) moduna** düşer — yani ekranda gördüğün modülasyon sonuçları rastgeledir.
Açılışta konsolda `[AI ENGINE] ONNX Modeli yüklendi!` satırını görüyorsan gerçek
model çalışıyor demektir.

## 3. Çalıştırma

```bash
python main.py
```

## 4. SDR bağlantısı

Uygulama SDR donanımına **doğrudan** bağlanmaz; araya ZMQ ile GNU Radio girer.

| Yön | Port | Protokol | Format |
|-----|------|----------|--------|
| RX (SDR → uygulama) | `tcp://127.0.0.1:5555` | ZMQ PUB/SUB — uygulama SUB | `complex64` akış |
| TX (uygulama → SDR) | `tcp://127.0.0.1:5556` | ZMQ — uygulama yayıncı | komut |

GNU Radio Companion tarafında akış şu şekilde kurulur:

```
[ Osmocom/SoapySDR Source ] → [ ZMQ PUB Sink: tcp://127.0.0.1:5555 ]
```

Önemli noktalar:

- GNU Radio çıkışı **complex64** olmalı (ZMQ PUB Sink varsayılanı).
- Örnekleme hızı `config.py` içindeki `SAMPLE_RATE` (500 kHz) ile aynı olsun.
- Uygulama her mesajdan `config.SDR_SEGMENT_LEN` (8192) örnek alır; GNU Radio
  tarafında vector length'i buna eşit ya da daha büyük tut, küçük olursa segment
  atlanır.
- Merkez frekansı `config.FC_TO_BAND` içindeki bantlardan biri olmalı
  (433 MHz / 868 MHz / 915 MHz / 2.4 GHz).

GNU Radio yayın yapmıyorsa uygulama açılır ama ED paneli boş kalır — hata vermez,
sadece veri beklemeye geçer.

### Donanım sürücüleri

`hardware/` altında HackRF, PlutoSDR ve USRP için sürücü sarmalayıcıları var.
Kullanacağın cihazın kendi sürücüsü (ör. HackRF için `libhackrf` + `gr-osmosdr`)
sistemde ayrıca kurulu olmalı.

## 5. Yapılandırma

`config.py` eğitim ve çıkarım tarafının **ortak** ayar dosyasıdır. Sahada
çalıştırmadan önce **iki ayarı mutlaka kontrol edin**:

### `SDR_CENTER_FREQ_HZ` — SDR'ı hangi frekansa ayarladıysanız

```python
SDR_CENTER_FREQ_HZ = 915_000_000.0   # Pluto 2.4 GHz'deyse: 2_400_000_000.0
```

Bu değer **elle** girilir, çünkü sistem bunu veriden çıkaramaz: Pluto karıştırıcıdan
sonra baseband örnek verir, bu örnekler merkez frekans bilgisi **taşımaz**. 915 MHz'den
de 2.4 GHz'den de alsanız örnekler aynı görünür.

Ekranda gösterilen mutlak frekans = `SDR_CENTER_FREQ_HZ` + (FFT'den ölçülen ofset).
Yani donanımı 2.4 GHz'e alıp burayı 915 MHz'de bırakırsanız **frekans yanlış gösterilir**.

> Modelde bir `band_logits` çıkışı var ama **kullanılmıyor**. Yukarıdaki sebeple o
> başlık bandı gerçekten bilemez, eğitim setindeki tesadüfi korelasyonu öğrenmiştir.
> Band her zaman ölçümden gelir. Model farklı bir band söylerse konsola uyarı düşer.

### `SIMULATION_MODE` — sahada her zaman `False`

```python
SIMULATION_MODE = False
```

`False` (varsayılan): arayüz **sadece** SDR'dan gerçek veri geldiğinde tespit gösterir.
Veri yokken ekran boş kalır, DF tarama modunda bekler — uydurma tespit üretilmez.

`True`: donanım yokken demo/geliştirme için sahte sinyal akıtır. Yarışmada açık
unutulursa ekranda gerçek olmayan tespitler akar.

Diğer ayarlar (örnekleme hızı, normalizasyon, sınıf isimleri, segment uzunluğu) da
bu dosyadadır.

> Sinyal/normalizasyon ayarlarını değiştirirseniz model yeniden eğitilmelidir.

## 6. Klasör yapısı

```
main.py            Uygulama girişi (buffer + AI + SDR + GUI'yi kurar)
config.py          Ortak konfigürasyon (eğitim & çıkarım)
core/              Dairesel buffer, durum yöneticisi, loglama
sdr_comms/         ZMQ alıcı / verici
ai_engine/         Önişleme, ONNX çıkarım, karar motoru
ed_module/         Sinyal tespiti, AOA/TDOA yön bulma, DSP
et_module/         Jammer, GPS/telsiz aldatma, dalga formu üretimi
hardware/          HackRF / Pluto / USRP sürücüleri
gui/               Ana pencere ve paneller
data/              ONNX modeli (ham IQ kayıtları repoya dahil değildir)
```

## 7. Sık karşılaşılan sorunlar

| Belirti | Sebep |
|---------|-------|
| `[AI ENGINE UYARISI] ... yüklenemedi` | `data/model.onnx.data` eksik ya da `onnxruntime` kurulu değil |
| Pencere açılıyor, ED paneli boş | GNU Radio 5555'ten yayın yapmıyor (beklenen davranış — sinyal gelince dolar) |
| Frekans yanlış gösteriliyor | `config.SDR_CENTER_FREQ_HZ` donanımdaki merkez frekansla aynı değil |
| Açılışta rastgele tespitler akıyor | `config.SIMULATION_MODE = True` kalmış, `False` yapın |
| Sinyal var ama tespit gelmiyor | SNR eşiği yüksek olabilir: `config.DETECTION_THRESHOLD_DB` düşürün |
| `ModuleNotFoundError: PyQt6` | Sanal ortam aktif değil ya da `pip install -r requirements.txt` çalıştırılmadı |
| Harita paneli boş | `PyQt6-WebEngine` kurulu değil |

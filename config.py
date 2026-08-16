"""
TEKNOFEST EH - Ortak Konfigürasyon
====================================
Bu dosya HEM eğitim (Colab) HEM inference (lokal proje) tarafından
kullanılır. Burada yapılan her değişiklik İKİSİNİ DE etkiler — bu
sayede eğitim ve gerçek zamanlı çıkarım her zaman uyumlu kalır.

Eğitim (preprocess_sdr.py): bu dosyayı import edip pipeline'ı buna göre kurar
Inference (ai_engine/preprocessor.py): bu dosyayı import edip aynı normalizasyonu uygular

KURAL: Bu dosyayı değiştirirsen modeli BAŞTAN eğitmen gerekir.
"""

# ============================================================
# SİNYAL & VERİ
# ============================================================
SAMPLE_RATE = 500_000        # Hz, tüm dosyalarda sabit
RAW_SAMPLE_LEN = 25_000      # Ham örneklem uzunluğu (h5 içinde)

# ============================================================
# PENCERELEME
# ============================================================
WINDOW_SIZE = 6250           # Modele girecek tensor uzunluğu
WINDOWS_PER_SAMPLE = 4       # 25000 / 6250 = 4

# ============================================================
# NORMALİZASYON
# ============================================================
# "rms"   -> her örneği RMS=1'e normalize et (önerilen)
# "fixed" -> her örneği sabit bir bölene böl
# "peak"  -> her örneği |max|'ına böl
NORMALIZATION = "rms"

# RMS için epsilon (sıfıra bölmeyi önler)
RMS_EPSILON = 1e-8

# Fixed normalizasyon için bölen (kullanılmıyor şu an, "fixed" seçilirse devreye girer)
FIXED_DIVISOR = 32768.0

# ============================================================
# SINIFLAR
# ============================================================
NUM_CLASSES = 6
MOD_NAMES = {
    0: "UNKNOWN",
    1: "BPSK",
    2: "QPSK",
    3: "8PSK",
    4: "16QAM",
    5: "64QAM",
}
NAME_TO_ID = {v: k for k, v in MOD_NAMES.items()}

# ============================================================
# FREKANS BANDI EŞLEMESİ
# ============================================================
# Center freq (Hz) -> band ID (0-3), 255 = geçersiz
FC_TO_BAND = {
    433_000_000.0: 0,   # 433 MHz
    868_000_000.0: 1,   # 868 MHz
    915_000_000.0: 2,   # 915 MHz
    2_400_000_000.0: 3, # 2.4 GHz
    0.0: 255,           # geçersiz/UNKNOWN
}
BAND_NAMES = {0: "433MHz", 1: "868MHz", 2: "915MHz", 3: "2.4GHz", 255: "INVALID"}

# ============================================================
# EĞİTİM SPLIT
# ============================================================
TRAIN_RATIO = 0.70
VAL_RATIO   = 0.15
TEST_RATIO  = 0.15
SEED = 42

# ============================================================
# MODEL GİRDİSİ
# ============================================================
# Model bekleyen tensor formatı: (batch, channels, length)
INPUT_CHANNELS = 2           # I, Q
INPUT_LENGTH = WINDOW_SIZE   # 6250 (eğitim penceresi)

# ============================================================
# INFERENCE / CANLI SDR (data/model.onnx ile uyumlu)
# ============================================================
# DİKKAT: Elimizdeki ONNX modelinin (data/model.onnx) 'iq_input' girdisi
# 2 x 8192'dir. Yukarıdaki WINDOW_SIZE=6250 eğitim tarafından kalmış eski
# bir değer ve bu modelle UYUŞMUYOR. Canlı çıkarımda gerçek uzunluk her
# zaman modelden okunur (InferenceEngine bunu dinamik yapar); aşağıdaki
# sabit sadece buffer/receiver'ın kaç örneklik segment toplayacağını belirler
# ve modelin beklediği uzunluğa eşit tutulmalıdır.
# NOT: Model başka bir uzunlukla yeniden eğitilirse burayı güncelleyin.
SDR_SEGMENT_LEN = 8192       # ZMQ receiver ve CircularBuffer segment uzunluğu

# SDR'ın o an AYARLI olduğu merkez frekans (Hz).
# Sistem bunu veriden ÇIKARAMAZ — donanıma ne yazdıysanız buraya da o yazılmalı.
# Ekranda gösterilen mutlak frekans = SDR_CENTER_FREQ_HZ + (FFT'den bulunan ofset).
# Pluto'yu 2.4 GHz'e alırsanız burayı da 2_400_000_000.0 yapın.
SDR_CENTER_FREQ_HZ = 915_000_000.0

# Spektrum / tespit
FFT_SIZE = 512               # Waterfall ve tepe tespiti için FFT nokta sayısı
DETECTION_THRESHOLD_DB = 8.0 # Gürültü tabanının kaç dB üstü "sinyal var" sayılsın

# ============================================================
# COĞRAFİ REFERANSLAR
# ============================================================
# Sistemin kurulu olduğu yer (GPS alıcı fix veremezse bu kullanılır).
HOME_NAME = "Elazığ"
HOME_LAT  = 38.6810
HOME_LON  = 39.2264
HOME_ALT  = 950.0

# GPS aldatmada sahte konumun sürükleneceği HEDEF.
# Gerçekçi bir GNSS spoofing mesafesi için Elazığ İÇİNDE/yakınında bir nokta
# kullanılıyor — şehirlerarası (~1000 km) sıçrama gerçekçi değildi.
SPOOF_TARGET_NAME = "Elazığ Havalimanı Yönü (~9-10 km)"
SPOOF_TARGET_LAT  = 38.6100
SPOOF_TARGET_LON  = 39.2900

# Sahte konum hedefe ne kadar sürede varsın (saniye). Küçültürsen hızlanır.
SPOOF_DRIFT_DURATION_S = 120.0

# ============================================================
# KONUM BULMA HARİTASI
# ============================================================
# Haritanın kapsadığı alanın kenar uzunluğu (metre). 1000 m = 1 km².
# Geniş harita (şehir ölçeği) hedefin kaydığını göstermez; dar alanda
# konum hatası gözle görülür.
MAP_AREA_SIZE_M = 1000.0

# SİMÜLASYON ANAHTARI
# False (varsayılan): arayüz SADECE SDR'dan gerçek veri geldiğinde tespit gösterir.
#   Veri yoksa ekran "SİNYAL YOK" durumunda bekler — uydurma tespit ÜRETİLMEZ.
# True: donanım yokken demo/geliştirme için sahte sinyal akıtır.
# SAHADA/YARIŞMADA HER ZAMAN False OLMALI.
SIMULATION_MODE = False

# Band ID -> temsili merkez frekans (FC_TO_BAND'in tersi)
BAND_TO_FC = {b: fc for fc, b in FC_TO_BAND.items() if b != 255}


def fc_to_band(fc_hz: float, tolerance_hz: float = 20e6) -> int:
    """Merkez frekansı en yakın tanımlı banda eşler. Hiçbiri yakın değilse 255."""
    best, best_diff = 255, tolerance_hz
    for ref_fc, band in FC_TO_BAND.items():
        if band == 255:
            continue
        diff = abs(fc_hz - ref_fc)
        if diff <= best_diff:
            best, best_diff = band, diff
    return best

# ============================================================
# ORTAK NORMALİZASYON FONKSİYONU
# ============================================================
import numpy as np

def normalize_iq(x: np.ndarray) -> np.ndarray:
    """
    IQ verisini config'deki yönteme göre normalize eder.

    Args:
        x: (..., 2, N) veya (2, N) shape'inde IQ verisi (float32 önerilen)

    Returns:
        Aynı shape'te normalize edilmiş veri (float32)

    KRİTİK: Bu fonksiyon HEM eğitimde HEM inference'ta kullanılır.
    Davranışı değişirse modeli yeniden eğitmek gerekir.
    """
    x = np.asarray(x, dtype=np.float32)

    if NORMALIZATION == "rms":
        # Per-sample RMS normalization: sqrt(mean(I^2 + Q^2)) = 1 olacak şekilde
        # Son iki eksen üzerinden hesapla (channels + length)
        if x.ndim == 2:  # (2, N) tek örnek
            rms = np.sqrt(np.mean(x ** 2))
            return x / (rms + RMS_EPSILON)
        else:  # (..., 2, N) batch
            axes = (-2, -1)
            rms = np.sqrt(np.mean(x ** 2, axis=axes, keepdims=True))
            return x / (rms + RMS_EPSILON)

    elif NORMALIZATION == "fixed":
        return x / FIXED_DIVISOR

    elif NORMALIZATION == "peak":
        if x.ndim == 2:
            peak = np.max(np.abs(x))
            return x / (peak + RMS_EPSILON)
        else:
            axes = (-2, -1)
            peak = np.max(np.abs(x), axis=axes, keepdims=True)
            return x / (peak + RMS_EPSILON)

    else:
        raise ValueError(f"Bilinmeyen NORMALIZATION: {NORMALIZATION}")


if __name__ == "__main__":
    # Hızlı sağlamlık testi
    print(f"Sample rate: {SAMPLE_RATE} Hz")
    print(f"Window size: {WINDOW_SIZE}")
    print(f"Normalizasyon: {NORMALIZATION}")
    print(f"Sınıf sayısı: {NUM_CLASSES}")

    # Test
    fake = (np.random.randn(2, 6250) * 1000).astype(np.float32)
    norm = normalize_iq(fake)
    print(f"\nTest: ham std={fake.std():.2f} -> normalize sonrası RMS={np.sqrt(np.mean(norm**2)):.4f}")

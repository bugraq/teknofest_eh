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
INPUT_LENGTH = WINDOW_SIZE   # 6250

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

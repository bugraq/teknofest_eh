"""
teknofest_eh/ai_engine/preprocessor.py
========================================
SDR donanimindan canli gelen IQ buffer'ini ONNX modelinin bekledigi
formata cevirir.

KRITIK: Bu dosya egitimdeki preprocess_sdr.py ile BIREBIR AYNI
        normalizasyonu yapar (config.normalize_iq). Aksi halde model
        egitimde gordugu sinyalden farkli bir sinyal gorur ve saglikli
        tahmin yapamaz.
"""

import numpy as np
from typing import Optional

# config.py'yi proje kokunden import et.
# Eger config.py teknofest_eh/ai_engine/ icinde degil de proje kokundeyse,
# import yolunu ona gore ayarla.
try:
    from .. import config  # teknofest_eh/config.py
except ImportError:
    try:
        import config       # PYTHONPATH'te ise
    except ImportError:
        # Son care: lokal kopya
        from pathlib import Path
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        import config


class Preprocessor:
    """
    Gercek zamanli IQ -> model girdisi cevirici.

    Kullanim:
        prep = Preprocessor()
        # SDR'dan gelen ham IQ buffer (genelde int16)
        raw_iq = np.array([[I0, I1, ...], [Q0, Q1, ...]], dtype=np.int16)
        # Modele hazir tensor (float32, batch=1)
        x = prep.process(raw_iq)
        # x.shape == (1, 2, 6250)
        outputs = onnx_session.run(None, {"input": x})
    """

    def __init__(self, window_size: Optional[int] = None):
        # Config'den oku - egitimle uyumlu kalsin
        self.window_size = window_size or config.WINDOW_SIZE
        self.normalization = config.NORMALIZATION

    # --------------------------------------------------------
    # Ana akis
    # --------------------------------------------------------
    def process(self, raw_iq_data) -> np.ndarray:
        """
        Ham IQ buffer'ini modelin bekledigi (1, 2, WINDOW_SIZE) tensorune
        cevirir.

        Args:
            raw_iq_data:
                - (2, N) int16/float - I ve Q kanallari ayri
                - (N, 2) int16/float - kanal son eksende (otomatik transpose)
                - (N,)   complex64    - kompleks IQ (otomatik ayristirilir)

        Returns:
            np.ndarray, shape (1, 2, WINDOW_SIZE), dtype float32
        """
        # 1. Numpy array'e cevir
        x = np.asarray(raw_iq_data)

        # 2. Shape'i (2, N)'e standardize et
        x = self._to_channel_first(x)

        # 3. Pencerele - tam window_size uzunlugunda olsun
        x = self._fit_window(x)

        # 4. float32'ye cevir
        x = x.astype(np.float32)

        # 5. Normalize et - egitimle birebir ayni!
        x = config.normalize_iq(x)

        # 6. Batch ekle: (2, N) -> (1, 2, N)
        x = np.expand_dims(x, axis=0)

        return x

    # --------------------------------------------------------
    # Yardimci fonksiyonlar
    # --------------------------------------------------------
    def _to_channel_first(self, x: np.ndarray) -> np.ndarray:
        """Farkli IQ formatlarini (2, N) shape'ine cevir."""
        # Kompleks ise I ve Q'ya ayir
        if np.iscomplexobj(x):
            return np.stack([x.real, x.imag], axis=0)

        if x.ndim == 1:
            raise ValueError(
                f"IQ verisi en az 2 boyutlu olmali, shape={x.shape}. "
                f"Kompleks veri kullaniyorsan dtype=complex64 yap."
            )

        if x.ndim == 2:
            # (2, N) zaten dogru
            if x.shape[0] == 2:
                return x
            # (N, 2) -> transpose
            if x.shape[1] == 2:
                return x.T
            raise ValueError(
                f"IQ shape {x.shape}: 2 kanal bekliyorum (2,N) veya (N,2)."
            )

        if x.ndim == 3:
            # Eger (1, 2, N) gibi batch'li geldiyse, batch'i cikar
            if x.shape[0] == 1 and x.shape[1] == 2:
                return x[0]
            if x.shape[0] == 1 and x.shape[2] == 2:
                return x[0].T

        raise ValueError(f"Desteklenmeyen IQ shape: {x.shape}")

    def _fit_window(self, x: np.ndarray) -> np.ndarray:
        """
        (2, N) shape'indeki sinyali (2, WINDOW_SIZE)'a sigdirir:
            - N > window_size: bastan kes (en son window_size sample'i al)
              -> SDR'da en taze veri sonda olur, eski veriyi atmak mantikli
            - N == window_size: degistirme
            - N < window_size: sifir-padding (sonu doldur)
        """
        n = x.shape[1]
        if n == self.window_size:
            return x
        if n > self.window_size:
            # En taze pencereyi al
            return x[:, -self.window_size:]
        # Eksikse padding - genelde olmamali, debug uyarisi
        pad = self.window_size - n
        return np.pad(x, ((0, 0), (0, pad)), mode="constant")


# ============================================================
# HIZLI SAGLAMLIK TESTI
# ============================================================
if __name__ == "__main__":
    prep = Preprocessor()

    # Senaryo 1: int16 (2, 25000) - SDR'dan tipik
    raw1 = np.random.randint(-30000, 30000, (2, 25000), dtype=np.int16)
    out1 = prep.process(raw1)
    print(f"Senaryo 1 (2,25000) int16 -> {out1.shape}, dtype={out1.dtype}")
    print(f"   RMS: {np.sqrt(np.mean(out1**2)):.4f} (RMS normalization ile ~1 olmali)")

    # Senaryo 2: float32 (N, 2) - bazi SDR backend'leri boyle verir
    raw2 = np.random.randn(6250, 2).astype(np.float32) * 1000
    out2 = prep.process(raw2)
    print(f"\nSenaryo 2 (6250,2) float32 -> {out2.shape}")

    # Senaryo 3: kompleks (N,) - GNU Radio tipik cikti
    raw3 = (np.random.randn(6250) + 1j * np.random.randn(6250)).astype(np.complex64)
    out3 = prep.process(raw3)
    print(f"\nSenaryo 3 ({len(raw3)},) complex64 -> {out3.shape}")

    # Senaryo 4: cok kisa buffer (padding)
    raw4 = np.random.randint(-1000, 1000, (2, 1000), dtype=np.int16)
    out4 = prep.process(raw4)
    print(f"\nSenaryo 4 (2,1000) [kisa] -> {out4.shape} (zero-padded)")

    print("\nTum senaryolar gecti.")

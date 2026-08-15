"""
ed_module/signal_detector.py
============================
Spektrum uzerinde sinyal var mi yok mu karari ve tepe frekansinin bulunmasi.

Arayuzdeki frekans degeri artik BURADAN gelir. Onceki halinde bu fonksiyonlar
bostu (pass) ve arayuz frekansi random.randint ile uyduruyordu.
"""

import numpy as np

try:
    import config
except ImportError:
    from .. import config


class DetectionResult:
    """Tek bir spektrum karesinin tespit sonucu."""

    __slots__ = ("present", "bin_index", "freq_offset_hz", "freq_hz",
                 "band_id", "band_name", "snr_db", "noise_floor_db")

    def __init__(self, present, bin_index, freq_offset_hz, freq_hz,
                 band_id, band_name, snr_db, noise_floor_db):
        self.present = present
        self.bin_index = bin_index
        self.freq_offset_hz = freq_offset_hz
        self.freq_hz = freq_hz
        self.band_id = band_id
        self.band_name = band_name
        self.snr_db = snr_db
        self.noise_floor_db = noise_floor_db

    def __repr__(self):
        if not self.present:
            return f"<Tespit YOK, taban={self.noise_floor_db:.1f} dB>"
        return (f"<Tespit {self.freq_hz/1e6:.3f} MHz ({self.band_name}), "
                f"SNR={self.snr_db:.1f} dB>")


class SignalDetector:
    """
    Spektrum uzerindeki sinyalleri tespit etmek (Energy Detection, CFAR) icin
    algoritmalar icerir.
    """

    def __init__(self, threshold=None, center_freq_hz=None):
        # Gurultu tabaninin kac dB ustu "sinyal" sayilsin
        self.threshold = config.DETECTION_THRESHOLD_DB if threshold is None else threshold
        self.center_freq_hz = (config.SDR_CENTER_FREQ_HZ
                               if center_freq_hz is None else center_freq_hz)

    def set_center_freq(self, fc_hz: float):
        """SDR baska bir banda ayarlandiginda arayuzden cagrilir."""
        self.center_freq_hz = float(fc_hz)

    def detect_energy(self, psd_db, freqs_hz=None) -> DetectionResult:
        """
        Basit enerji tespiti: gurultu tabanini medyandan kestirir, en guclu bin
        tabandan threshold kadar yukarideyse sinyal var der.

        Medyan kullaniliyor cunku ortalama, guclu bir tasiyici varken tabani
        yukari cekip sinyalin kendisini gizler.
        """
        psd = np.asarray(psd_db, dtype=np.float32)
        noise_floor = float(np.median(psd))

        peak_idx = int(np.argmax(psd))
        peak_db = float(psd[peak_idx])
        snr_db = peak_db - noise_floor
        present = snr_db >= self.threshold

        n = len(psd)
        if freqs_hz is not None:
            freqs = np.asarray(freqs_hz, dtype=np.float64)
        else:
            # freqs verilmediyse bin indeksinden yeniden turet
            freqs = (np.arange(n) - n / 2.0) * (config.SAMPLE_RATE / n)

        # Merkez frekans tahmini: tek tepe bini DEGIL, sinyalin guc agirlikli
        # merkezi. Modulasyonlu sinyal birden fazla bine yayilir (QPSK'de ana lob
        # sembol hizi kadar genis); tek tepeye bakinca gurultu tepeyi lob icinde
        # gezdirir ve olculen frekans oynar. Centroid bunu ortadan kaldirir.
        centroid_idx = peak_idx
        if present:
            half_db = noise_floor + snr_db / 2.0
            above = psd >= half_db
            # Tepeyi iceren bitisik bolgeyi bul (yandaki baska sinyale tasmasin)
            lo = peak_idx
            while lo > 0 and above[lo - 1]:
                lo -= 1
            hi = peak_idx
            while hi < n - 1 and above[hi + 1]:
                hi += 1
            # dB -> lineer guc; agirliklardan gurultu tabanini cikar
            lin = np.power(10.0, (psd[lo:hi + 1] - noise_floor) / 10.0) - 1.0
            lin = np.clip(lin, 0.0, None)
            if lin.sum() > 0:
                offset = float(np.average(freqs[lo:hi + 1], weights=lin))
                centroid_idx = int(round(np.average(np.arange(lo, hi + 1), weights=lin)))
            else:
                offset = float(freqs[peak_idx])
        else:
            offset = float(freqs[peak_idx])

        freq_hz = self.center_freq_hz + offset
        band_id = config.fc_to_band(self.center_freq_hz)
        band_name = config.BAND_NAMES.get(band_id, "INVALID")

        return DetectionResult(
            present=present,
            bin_index=centroid_idx,
            freq_offset_hz=offset,
            freq_hz=freq_hz,
            band_id=band_id,
            band_name=band_name,
            snr_db=snr_db,
            noise_floor_db=noise_floor,
        )

    def cfar_detect(self, psd_db, guard=2, train=8, pfa_db=None):
        """
        Constant False Alarm Rate (CFAR) ile dinamik sinyal tespiti.

        Her bin icin, etrafindaki 'train' hucrenin ortalamasini (aradaki 'guard'
        hucreleri haric tutarak) yerel gurultu tahmini olarak kullanir. Genis
        bantli girisim varken sabit esikten cok daha saglamdir.

        Returns:
            (mask, threshold_db) - mask: sinyal bulunan binler (bool dizi)
        """
        psd = np.asarray(psd_db, dtype=np.float32)
        n = len(psd)
        offset_db = self.threshold if pfa_db is None else pfa_db

        half = guard + train
        padded = np.pad(psd, half, mode="edge")

        # Kayan pencere toplamlari: tum pencere - koruma bolgesi = egitim hucreleri
        win = 2 * half + 1
        cumsum = np.cumsum(np.insert(padded, 0, 0.0))
        total = cumsum[win:] - cumsum[:-win]

        gwin = 2 * guard + 1
        gcum = np.cumsum(np.insert(padded[train:len(padded) - train], 0, 0.0))
        guard_sum = gcum[gwin:] - gcum[:-gwin]

        n_train = win - gwin
        local_noise = (total[:n] - guard_sum[:n]) / max(n_train, 1)

        threshold_db = local_noise + offset_db
        return psd > threshold_db, threshold_db

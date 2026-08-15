"""
ed_module/dsp_utils.py
======================
Ham IQ verisi uzerinde calisan temel DSP fonksiyonlari.

Waterfall ekrani ve frekans tespiti bu dosyadaki perform_fft() ciktisini
kullanir. Daha once bu fonksiyonlar bos (pass) birakilmisti; o yuzden arayuz
spektrumu uyduruyordu.
"""

import numpy as np
from scipy import signal as sp_signal


def _to_complex(iq_data) -> np.ndarray:
    """(2, N) I/Q matrisini veya kompleks diziyi tek tip complex64'e cevirir."""
    x = np.asarray(iq_data)
    if np.iscomplexobj(x):
        return x.astype(np.complex64)
    if x.ndim == 2 and x.shape[0] == 2:
        return (x[0] + 1j * x[1]).astype(np.complex64)
    if x.ndim == 2 and x.shape[1] == 2:
        return (x[:, 0] + 1j * x[:, 1]).astype(np.complex64)
    raise ValueError(f"Desteklenmeyen IQ shape: {x.shape}")


def perform_fft(iq_data, sample_rate, fft_size=512):
    """
    Zaman uzayindaki IQ verisinin spektrumunu (FFT) cikarir.

    Args:
        iq_data:     (2, N) I/Q matrisi veya (N,) complex64
        sample_rate: Ornekleme hizi (Hz)
        fft_size:    Cikti bin sayisi

    Returns:
        freqs_hz: (fft_size,) merkez frekansa gore ofset, Hz, artan sirali
        psd_db:   (fft_size,) guc spektrumu, dB

    Not: Kompleks IQ oldugu icin spektrum merkez frekansin HEM altini HEM
    ustunu kapsar (-fs/2 .. +fs/2). fftshift ile negatif frekanslar sola alinir,
    boylece ekrandaki sol-sag ekseni gercek frekansla ayni yonde olur.
    """
    x = _to_complex(iq_data)

    # Segment fft_size'dan uzunsa Welch benzeri ortalama al: gurultu tabani
    # oturur, tek seferlik FFT'nin cirpintisi kaybolur.
    n = len(x)
    if n < fft_size:
        x = np.pad(x, (0, fft_size - n))
        n = fft_size

    window = np.hanning(fft_size).astype(np.float32)
    n_seg = n // fft_size
    acc = np.zeros(fft_size, dtype=np.float64)
    for i in range(n_seg):
        seg = x[i * fft_size:(i + 1) * fft_size] * window
        acc += np.abs(np.fft.fftshift(np.fft.fft(seg))) ** 2
    acc /= max(n_seg, 1)

    psd_db = 10.0 * np.log10(acc + 1e-12)
    freqs_hz = np.fft.fftshift(np.fft.fftfreq(fft_size, d=1.0 / sample_rate))
    return freqs_hz.astype(np.float32), psd_db.astype(np.float32)


def apply_filter(iq_data, filter_type, cutoff, fs, order=5):
    """
    I/Q verisine alcak geciren (LPF) veya bant geciren (BPF) filtre uygular.

    filter_type: "lpf" | "bpf"
    cutoff:      LPF icin tek sayi (Hz), BPF icin (dusuk, yuksek) demeti
    """
    x = _to_complex(iq_data)
    nyq = fs / 2.0

    if filter_type.lower() == "lpf":
        wn = np.clip(cutoff / nyq, 1e-6, 0.999)
        b, a = sp_signal.butter(order, wn, btype="low")
    elif filter_type.lower() == "bpf":
        low, high = cutoff
        wn = [np.clip(low / nyq, 1e-6, 0.998), np.clip(high / nyq, 2e-6, 0.999)]
        b, a = sp_signal.butter(order, wn, btype="band")
    else:
        raise ValueError(f"Bilinmeyen filtre tipi: {filter_type}")

    # Kompleks sinyalde I ve Q'yu ayri filtrelemek faz bozar; filtfilt kompleks
    # diziyi dogrudan isleyebilir ve sifir faz kaymasi verir.
    return sp_signal.filtfilt(b, a, x).astype(np.complex64)


def calculate_rssi(iq_data) -> float:
    """
    Sinyal guc seviyesini dB cinsinden hesaplar (bagil).

    NOT: Bu MUTLAK dBm DEGILDIR. Gercek dBm icin SDR'in kazanc (gain) ayari ve
    anten/kablo kaybi bilinmelidir; Pluto ham ADC sayisi verir. Karsilastirma ve
    esikleme icin kullanilabilir, "sahada olculen guc" diye raporlanamaz.
    """
    x = _to_complex(iq_data)
    power = np.mean(np.abs(x) ** 2)
    return float(10.0 * np.log10(power + 1e-12))

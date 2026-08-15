import threading

import numpy as np

try:
    import config
except ImportError:
    from .. import config


class StateManager:
    def __init__(self):
        self.lock = threading.Lock()

        # --- ED (Elektronik Destek) Durumu ---
        self.current_modulation = "Bekleniyor..."
        self.current_snr = 0.0
        self.ai_confidence = 0.0

        # Tespit edilen sinyalin ÖLÇÜLEN frekansı (uydurma değil, FFT tepesinden)
        self.detected_freq_hz = 0.0
        self.detected_band = "—"

        # --- Canlı Spektrum (waterfall bunu çizer) ---
        self.signal_present = False
        self.spectrum_db = None        # (FFT_SIZE,) dB, SDR'dan gelen gerçek spektrum
        self.spectrum_peak_bin = 0     # Tespit edilen tepenin bin indeksi
        self.noise_floor_db = 0.0
        self.has_live_data = False     # SDR'dan bir kez bile veri geldi mi?

        # --- ET (Elektronik Taarruz) Durumu ---
        self.jamming_active = False
        self.target_freq = 2400.0
        self.jamming_type = "BEKLEMEDE"

        # --- GPS Aldatma Durumu ---
        self.gps_spoof_active = False
        self.gps_spoof_lat    = 0.0
        self.gps_spoof_lon    = 0.0
        self.gps_spoof_alt    = 0.0

        # --- GNS/GNSS Aldatma Durumu ---
        self.gns_spoof_active        = False
        self.gns_spoof_constellations: list = []
        self.gns_spoof_mode          = ""
        self.gns_spoof_pos_offset_m  = 0.0
        self.gns_spoof_time_offset_ms = 0.0

    def update_ed_state(self, mod, snr, conf, freq_hz=None, band=None):
        """ Yapay Zeka (AI) modülü bu fonksiyonu kullanarak kararını sisteme yazar """
        with self.lock:
            self.current_modulation = mod
            self.current_snr = snr
            self.ai_confidence = conf
            if freq_hz is not None:
                self.detected_freq_hz = float(freq_hz)
            if band is not None:
                self.detected_band = band

    def clear_ed_state(self):
        """
        Spektrumda sinyal yokken çağrılır: ED göstergeleri boşa döner.

        Bu olmadan son tespit ekranda asılı kalır ve sinyal kesildikten sonra
        da 'tespit var' gibi görünür.
        """
        with self.lock:
            self.current_modulation = "SİNYAL YOK"
            self.current_snr = 0.0
            self.ai_confidence = 0.0
            self.detected_freq_hz = 0.0
            self.detected_band = "—"

    def update_spectrum(self, psd_db, detection):
        """
        ED motoru her spektrum karesinde çağırır. Waterfall/IQ ekranı buradan
        beslenir — artık sahte FFT üretilmiyor.
        """
        with self.lock:
            self.spectrum_db = np.asarray(psd_db, dtype=np.float32)
            self.signal_present = bool(detection.present)
            self.spectrum_peak_bin = int(detection.bin_index)
            self.noise_floor_db = float(detection.noise_floor_db)
            self.has_live_data = True

    def update_et_state(self, active, freq, jam_type):
        """ Arayüzdeki (GUI) butonlara basıldığında taarruz durumu güncellenir """
        with self.lock:
            self.jamming_active = active
            self.target_freq = freq
            self.jamming_type = jam_type

    def update_gps_spoof_state(self, active: bool, lat: float, lon: float, alt: float):
        """ GPS aldatma paneli tarafından çağrılır """
        with self.lock:
            self.gps_spoof_active = active
            self.gps_spoof_lat    = lat
            self.gps_spoof_lon    = lon
            self.gps_spoof_alt    = alt

    def update_gns_spoof_state(self, active: bool, constellations: list,
                                mode: str, pos_offset_m: float, time_offset_ms: float):
        """ GNSS aldatma paneli tarafından çağrılır """
        with self.lock:
            self.gns_spoof_active         = active
            self.gns_spoof_constellations = constellations
            self.gns_spoof_mode           = mode
            self.gns_spoof_pos_offset_m   = pos_offset_m
            self.gns_spoof_time_offset_ms = time_offset_ms

    def get_state(self):
        """ Arayüz, ekrandaki yazıları güncellemek için bu fonksiyonu saniyede 60 kez çağırır """
        with self.lock:
            return {
                # ED
                "mod":  self.current_modulation,
                "snr":  self.current_snr,
                "conf": self.ai_confidence,
                # ED — ölçülen frekans/band ve canlı spektrum
                "detected_freq_hz": self.detected_freq_hz,
                "detected_band":    self.detected_band,
                "signal_present":   self.signal_present,
                "spectrum_db":      self.spectrum_db,
                "peak_bin":         self.spectrum_peak_bin,
                "noise_floor":      self.noise_floor_db,
                "has_live_data":    self.has_live_data,
                # ET Taarruz
                "jam_active": self.jamming_active,
                "freq":       self.target_freq,
                "jam_type":   self.jamming_type,
                # GPS Aldatma
                "gps_active": self.gps_spoof_active,
                "gps_lat":    self.gps_spoof_lat,
                "gps_lon":    self.gps_spoof_lon,
                "gps_alt":    self.gps_spoof_alt,
                # GNS Aldatma
                "gns_active":        self.gns_spoof_active,
                "gns_constellations": self.gns_spoof_constellations,
                "gns_mode":          self.gns_spoof_mode,
                "gns_pos_offset":    self.gns_spoof_pos_offset_m,
                "gns_time_offset":   self.gns_spoof_time_offset_ms,
            }
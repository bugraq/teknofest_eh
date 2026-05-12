import threading

class StateManager:
    def __init__(self):
        self.lock = threading.Lock()
        
        # --- ED (Elektronik Destek) Durumu ---
        self.current_modulation = "Bekleniyor..."
        self.current_snr = 0.0
        self.ai_confidence = 0.0
        
        # --- ET (Elektronik Taarruz) Durumu ---
        self.jamming_active = False
        self.target_freq = 2400.0 # Başlangıç frekansı (Örn: 2400 MHz)
        self.jamming_type = "BEKLEMEDE"

    def update_ed_state(self, mod, snr, conf):
        """ Yapay Zeka (AI) modülü bu fonksiyonu kullanarak kararını sisteme yazar """
        with self.lock:
            self.current_modulation = mod
            self.current_snr = snr
            self.ai_confidence = conf

    def update_et_state(self, active, freq, jam_type):
        """ Arayüzdeki (GUI) butonlara basıldığında taarruz durumu güncellenir """
        with self.lock:
            self.jamming_active = active
            self.target_freq = freq
            self.jamming_type = jam_type

    def get_state(self):
        """ Arayüz, ekrandaki yazıları güncellemek için bu fonksiyonu saniyede 60 kez çağırır """
        with self.lock:
            return {
                "mod": self.current_modulation,
                "snr": self.current_snr,
                "conf": self.ai_confidence,
                "jam_active": self.jamming_active,
                "freq": self.target_freq,
                "jam_type": self.jamming_type
            }
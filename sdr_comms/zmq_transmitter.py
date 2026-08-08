import zmq
import json
import threading
import time

class ZMQTransmitter:
    def __init__(self, state_manager, port=5556):
        self.state_manager = state_manager
        self.port = port
        # ZMQ Ayarları: GNU Radio'ya emir YAYINLAYAN (PUB) taraf biziz
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUB)
        self.socket.bind(f"tcp://127.0.0.1:{self.port}")
        self.is_running = False

    def start(self):
        """ Taarruz kontrolcüsünü arkaplanda başlatır """
        self.is_running = True
        self.thread = threading.Thread(target=self._transmit_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.is_running = False
        # Thread'in döngüden çıkmasını bekle, sonra soketi/context'i temizle
        thread = getattr(self, "thread", None)
        if thread is not None:
            thread.join(timeout=1.0)
        try:
            self.socket.close(linger=0)
            self.context.term()
        except Exception:
            pass

    def _transmit_loop(self):
        print(f"[SDR-TX] Taarruz/Jamming yayın portu ({self.port}) aktif...")
        while self.is_running:
            # 1. Sistemin güncel durumunu (Arayüzdeki butonları) kontrol et
            state = self.state_manager.get_state()
            
            # 2. GNU Radio'nun anlayacağı basit bir JSON emri hazırla
            command = {
                "jamming_active": state["jam_active"],
                "target_freq_mhz": state["freq"],
                "jamming_type": state["jam_type"]
            }
            
            # 3. Eğer butona basılmışsa (Aktifse), emri radyoya fırlat!
            if command["jamming_active"]:
                self.socket.send_string(json.dumps(command))
            
            # Saniyede 10 kere emir basması yeterlidir
            time.sleep(0.1)
import zmq
import numpy as np
import threading
import time

try:
    import config
except ImportError:
    from .. import config

class ZMQReceiver:
    def __init__(self, circular_buffer, port=5555):
        self.buffer = circular_buffer
        self.port = port
        # Modele girecek segment uzunluğu (config.SDR_SEGMENT_LEN = 8192)
        self.segment_len = config.SDR_SEGMENT_LEN
        # ZMQ Ayarları: GNU Radio'dan gelen veriye ABONE (SUB) oluyoruz
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.connect(f"tcp://127.0.0.1:{self.port}")
        self.socket.setsockopt_string(zmq.SUBSCRIBE, "") # Her şeyi dinle
        self.is_running = False

    def start(self):
        """ Dinleme işlemini arkaplanda (Thread) başlatır """
        self.is_running = True
        self.thread = threading.Thread(target=self._receive_loop, daemon=True)
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

    def _receive_loop(self):
        print(f"[SDR-RX] Radyo dinleme portu ({self.port}) açıldı...")
        while self.is_running:
            try:
                # ZMQ'dan gelen ham baytları al (NOBLOCK: Veri yoksa kodu dondurma)
                raw_bytes = self.socket.recv(flags=zmq.NOBLOCK)
                
                # GNU Radio veriyi "complex64" gönderir, bunu numpy dizisine çeviriyoruz
                complex_data = np.frombuffer(raw_bytes, dtype=np.complex64)
                
                # Veriyi I (Reel) ve Q (Sanal) olarak ayırıp modelin beklediği
                # (2, SDR_SEGMENT_LEN=8192) formatına sok
                if len(complex_data) >= self.segment_len:
                    segment = complex_data[:self.segment_len]
                    iq_matrix = np.array([segment.real, segment.imag], dtype=np.float32)
                    
                    # Veriyi depoya (Buffer) bas!
                    self.buffer.push(iq_matrix)
                    
            except zmq.Again:
                # Eğer o an radyodan veri gelmiyorsa CPU'yu yorma, 1 milisaniye bekle
                time.sleep(0.001)
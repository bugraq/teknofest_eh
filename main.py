import sys
from PyQt6.QtWidgets import QApplication

# --- KENDİ MODÜLLERİMİZ ---
from core.circular_buffer import CircularBuffer
from core.state_manager import StateManager
from ai_engine.inferencer import InferenceEngine
from sdr_comms.zmq_receiver import ZMQReceiver
from sdr_comms.zmq_transmitter import ZMQTransmitter
from gui.main_window import MainWindow

def main():
    # 1. TEMEL BİLEŞENLERİ OLUŞTUR
    buffer = CircularBuffer(buffer_size=5000, segment_length=1024)
    state_manager = StateManager()

    # 2. SDR (DONANIM) HABERLEŞMESİNİ BAŞLAT
    sdr_rx = ZMQReceiver(buffer, port=5555)
    sdr_tx = ZMQTransmitter(state_manager, port=5556)
    sdr_rx.start()
    sdr_tx.start()

    # 3. YAPAY ZEKA MOTORUNU BAŞLAT
    ai_engine = InferenceEngine(buffer, state_manager)
    ai_engine.start()
    print("[SİSTEM] Yapay Zeka Motoru arkaplanda uyandırıldı...")

    # 4. ARAYÜZÜ (GUI) BAŞLAT
    app = QApplication(sys.argv)  # <--- Hatanın sebebi buranın eksik olmasıydı
    
    # Arayüze, sistem hafızasını (buffer) ve durumunu (state) gönderiyoruz
    window = MainWindow(buffer, state_manager)
    window.show()

    # 5. UYGULAMA ÇIKIŞINDA TEMİZLİK YAP
    exit_code = app.exec()
    
    # Çarpıya basıp çıkarken arkada açık kalan portları ve yapay zekayı kapat
    sdr_rx.stop()
    sdr_tx.stop()
    ai_engine.stop() 
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
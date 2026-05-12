import time
import threading
import numpy as np
import onnxruntime as ort
from ai_engine.preprocessor import Preprocessor

class InferenceEngine:
    def __init__(self, circular_buffer, state_manager, model_path="data/model.onnx"):
        self.buffer = circular_buffer
        self.state_manager = state_manager
        self.preprocessor = Preprocessor()
        self.is_running = False
        
        self.classes = ["BPSK", "QPSK", "8-PSK", "16-QAM", "64-QAM"]
        
        # ONNX Modelini Yüklemeyi Dene
        self.use_fake_ai = False
        try:
            self.ort_session = ort.InferenceSession(model_path)
            self.input_name = self.ort_session.get_inputs()[0].name
            print("[AI ENGINE] ONNX Modeli başarıyla yüklendi!")
        except Exception as e:
            print(f"[AI ENGINE UYARISI] {model_path} bulunamadı! Simülasyon (Fake AI) modunda çalışacak.")
            self.use_fake_ai = True # Elimizde henüz gerçek model yoksa kod çökmesin diye

    def start(self):
        """ Yapay zekayı ayrı bir iş parçacığında (Thread) başlatır """
        self.is_running = True
        self.thread = threading.Thread(target=self._run_inference_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.is_running = False

    def _run_inference_loop(self):
        while self.is_running:
            # 1. Depodan yeni veriyi çek
            raw_data = self.buffer.pop()
            
            if raw_data is not None:
                # 2. Veriyi modele hazırla
                processed_data = self.preprocessor.process(raw_data)
                
                # 3. Modele Tahmin Yaptır
                if not self.use_fake_ai:
                    # GERÇEK ONNX ÇIKARIMI (Işık Hızında)
                    ort_inputs = {self.input_name: processed_data}
                    ort_outs = self.ort_session.run(None, ort_inputs)
                    
                    probabilities = ort_outs[0][0]
                    class_idx = np.argmax(probabilities)
                    confidence = float(np.max(probabilities)) * 100
                    detected_mod = self.classes[class_idx]
                    
                    # SNR tahmini için sahte veya kural tabanlı bir mantık (ET için lazım)
                    estimated_snr = round(np.random.uniform(5, 20), 1) 
                    
                else:
                    # SİMÜLASYON (Model yoksa test için rastgele sonuç üretir)
                    detected_mod = np.random.choice(self.classes)
                    confidence = round(np.random.uniform(75.0, 99.9), 1)
                    estimated_snr = round(np.random.uniform(-5, 20), 1)
                    time.sleep(0.5) # Yapay zeka hesaplıyormuş gibi bekle

                # 4. Çıkan sonucu Sistemin Hafızasına (State Manager) yaz!
                self.state_manager.update_ed_state(detected_mod, estimated_snr, confidence)
                
            else:
                # Eğer depoda okunacak veri kalmadıysa CPU'yu yorma, biraz dinlen
                time.sleep(0.01)
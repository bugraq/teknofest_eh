import time
import threading
from pathlib import Path
import numpy as np
import onnxruntime as ort
from ai_engine.preprocessor import Preprocessor

try:
    from .. import config
except ImportError:
    import config


# Model yolu proje kokune gore cozulur; boylece uygulama hangi klasorden
# calistirilirsa calistirilsin (IDE, farkli cwd, kisayol) model bulunur.
DEFAULT_MODEL_PATH = Path(__file__).resolve().parent.parent / "data" / "model.onnx"


def _softmax(logits: np.ndarray) -> np.ndarray:
    """Ham logit vektörünü olasılığa çevirir (sayısal olarak kararlı)."""
    z = np.asarray(logits, dtype=np.float64)
    z = z - np.max(z)
    e = np.exp(z)
    return e / (np.sum(e) + 1e-12)


class InferenceEngine:
    def __init__(self, circular_buffer, state_manager, model_path=None):
        model_path = str(model_path or DEFAULT_MODEL_PATH)
        self.buffer = circular_buffer
        self.state_manager = state_manager
        self.is_running = False

        # Sınıf isimleri config'den gelir — model çıktısıyla (mod_logits, 6 sınıf)
        # BİREBİR aynı sıradadır. Elle liste tutmak indeks kaymasına yol açardı.
        self.classes = [config.MOD_NAMES[i] for i in range(config.NUM_CLASSES)]

        # ONNX Modelini Yüklemeyi Dene
        self.use_fake_ai = False
        self.mod_output_name = None
        try:
            self.ort_session = ort.InferenceSession(model_path)
            self.input_name = self.ort_session.get_inputs()[0].name

            # Modelin beklediği gerçek girdi uzunluğunu MODELDEN oku (örn. 8192).
            # Böylece config/buffer yanlış olsa bile preprocessor doğru uzunluğa çevirir.
            in_shape = self.ort_session.get_inputs()[0].shape
            model_len = in_shape[-1] if isinstance(in_shape[-1], int) else config.SDR_SEGMENT_LEN
            self.preprocessor = Preprocessor(window_size=model_len)

            # Model çok başlıklı (mod/band/env/cond). Modülasyon başlığını İSİMLE seç,
            # sıraya güvenme. İsim yoksa ilk çıktıya düş.
            out_names = [o.name for o in self.ort_session.get_outputs()]
            self.mod_output_name = "mod_logits" if "mod_logits" in out_names else out_names[0]

            print(f"[AI ENGINE] ONNX Modeli yüklendi! Girdi uzunluğu={model_len}, "
                  f"çıktılar={out_names}, mod başlığı='{self.mod_output_name}'")
        except Exception as e:
            print(f"[AI ENGINE UYARISI] {model_path} yüklenemedi ({e}). "
                  f"Simülasyon (Fake AI) modunda çalışacak.")
            self.use_fake_ai = True  # Elimizde henüz gerçek model yoksa kod çökmesin diye
            self.preprocessor = Preprocessor(window_size=config.SDR_SEGMENT_LEN)

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
                    # Model batch=1'e sabit; preprocessor zaten (1, 2, N) veriyor.
                    ort_inputs = {self.input_name: processed_data}
                    ort_outs = self.ort_session.run([self.mod_output_name], ort_inputs)

                    # Model ham LOGIT döndürür -> önce softmax, sonra güven skoru.
                    logits = np.asarray(ort_outs[0])[0]
                    probabilities = _softmax(logits)
                    class_idx = int(np.argmax(probabilities))
                    confidence = float(probabilities[class_idx]) * 100
                    detected_mod = self.classes[class_idx]

                    # NOT: Modelde SNR başlığı YOK. SNR şimdilik tahmini/simülasyon.
                    # Gerçek SNR istenirse ED tarafında ayrı hesaplanmalı.
                    estimated_snr = round(np.random.uniform(5, 20), 1)

                else:
                    # SİMÜLASYON (Model yoksa test için rastgele sonuç üretir)
                    # UNKNOWN'ı (indeks 0) elemeden seçiyoruz ki sim gerçek bir
                    # modülasyon tespiti gibi görünsün.
                    sim_classes = [c for c in self.classes if c != "UNKNOWN"]
                    detected_mod = np.random.choice(sim_classes)
                    confidence = round(np.random.uniform(75.0, 99.9), 1)
                    estimated_snr = round(np.random.uniform(-5, 20), 1)
                    time.sleep(0.5) # Yapay zeka hesaplıyormuş gibi bekle

                # 4. Çıkan sonucu Sistemin Hafızasına (State Manager) yaz!
                self.state_manager.update_ed_state(detected_mod, estimated_snr, confidence)
                
            else:
                # Eğer depoda okunacak veri kalmadıysa CPU'yu yorma, biraz dinlen
                time.sleep(0.01)
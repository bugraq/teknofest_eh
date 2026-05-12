import numpy as np
import threading

class CircularBuffer:
    def __init__(self, buffer_size=5000, segment_length=1024):
        """
        buffer_size: Hafızada aynı anda tutulacak maksimum paket sayısı
        segment_length: AI modeline girecek olan IQ veri boyutu (1024)
        """
        # RAM'i şişirmemek için baştan 5000 adetlik yer ayırıyoruz (Pre-allocation)
        # Tip kesinlikle float32 olmalı (Yapay Zeka için)
        self.buffer = np.zeros((buffer_size, 2, segment_length), dtype=np.float32)
        self.buffer_size = buffer_size
        
        self.head = 0  # Yeni verinin yazılacağı nokta
        self.tail = 0  # AI modelinin veriyi çekeceği nokta
        self.lock = threading.Lock() # Thread'lerin çarpışmasını önler

    def push(self, iq_data):
        """ ZMQ'dan gelen canlı veriyi depoya basar """
        with self.lock:
            self.buffer[self.head] = iq_data
            self.head = (self.head + 1) % self.buffer_size
            
            # Eğer depo dolduysa ve head tail'e yetiştiyse, en eski veriyi ez
            if self.head == self.tail:
                self.tail = (self.tail + 1) % self.buffer_size

    def pop(self):
        """ Yapay zeka motorunun depodan veri çekmesini sağlar """
        with self.lock:
            # Eğer okunacak yeni veri yoksa None döndür
            if self.head == self.tail:
                return None 
            
            data = self.buffer[self.tail].copy() # Veriyi al
            self.tail = (self.tail + 1) % self.buffer_size # Kuyruğu ilerlet
            return data
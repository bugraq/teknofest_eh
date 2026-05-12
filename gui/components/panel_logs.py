from PyQt6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QGroupBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from datetime import datetime

class SignalLogPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # --- SİNYAL LOGLARI KUTUSU ---
        self.log_group = QGroupBox("CANLI SİNYAL LOGLARI")
        self.log_group.setStyleSheet("QGroupBox { border: 1px solid #334155; margin-top: 15px; font-weight: bold; color: #10b981; font-size: 13px; } QGroupBox::title { padding: 0 5px; }")
        self.log_layout = QVBoxLayout()
        self.log_layout.setContentsMargins(5, 20, 5, 5)

        # Liste Widget'ı (Terminal görünümlü)
        self.log_list = QListWidget()
        self.log_list.setWordWrap(True) # Yatay taşmayı engelle, alt satıra geç
        self.log_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff) # Yatay kaydırma çubuğunu gizle
        self.log_list.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                border: none;
                color: #f8fafc;
                font-family: 'Segoe UI', 'Inter', sans-serif;
                font-size: 13px;
                padding: 5px;
                outline: none;
            }
            QListWidget::item {
                border-bottom: 1px solid #334155;
                padding: 10px 5px;
            }
            QListWidget::item:selected {
                background-color: #334155;
            }
        """)
        
        self.log_layout.addWidget(self.log_list)
        self.log_group.setLayout(self.log_layout)
        
        self.layout.addWidget(self.log_group)

    def add_log(self, modulation, snr, confidence):
        """ Yapay zekadan gelen veriyi log ekranına basar """
        # Anlık saati al
        now = datetime.now().strftime("%H:%M:%S")
        
        # Log metnini hazırla
        log_text = f"[{now}] TESPİT: {modulation} | SNR: {snr}dB | GÜVEN: %{confidence}"
        item = QListWidgetItem(log_text)
        
        # Güven skoruna göre askeri renklendirme (Hedef kesinleşirse Kırmızı)
        if confidence >= 95.0:
            item.setForeground(QColor("#ef4444")) # Kırmızı (Yüksek Tehdit)
        elif confidence >= 90.0:
            item.setForeground(QColor("#f59e0b")) # Sarı (Olası Tehdit)
        else:
            item.setForeground(QColor("#10b981")) # Yeşil (Standart)
            
        # Yeni logu en üste ekle
        self.log_list.insertItem(0, item)
        
        # RAM şişmesin diye listede en fazla 50 kayıt tut, eskileri sil
        if self.log_list.count() > 50:
            self.log_list.takeItem(50)
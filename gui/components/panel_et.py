from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, 
                             QPushButton, QComboBox, QSlider, QGroupBox)
from PyQt6.QtCore import Qt

class ControlPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # --- 1. ED (ELEKTRONİK DESTEK / AI) KUTUSU ---
        self.ed_group = QGroupBox("BİLİŞSEL ED DURUMU")
        self.ed_group.setStyleSheet("QGroupBox { border: 1px solid #334155; margin-top: 15px; font-weight: bold; color: #3b82f6; font-size: 13px; } QGroupBox::title { padding: 0 5px; }")
        self.ed_layout = QVBoxLayout()
        self.ed_layout.setSpacing(10)
        self.ed_layout.setContentsMargins(15, 20, 15, 15)
        
        self.lbl_modulation = QLabel("Hedef Sinyal: ARANIYOR...")
        self.lbl_modulation.setStyleSheet("color: #f8fafc; font-size: 15px; font-weight: bold; background: transparent; border: none;")
        
        self.lbl_snr = QLabel("Tahmini SNR: -- dB")
        self.lbl_snr.setStyleSheet("color: #94a3b8; font-size: 13px; background: transparent; border: none;")
        
        self.lbl_confidence = QLabel("Yapay Zeka Güven Skoru: %0")
        self.lbl_confidence.setStyleSheet("color: #94a3b8; font-size: 13px; background: transparent; border: none;")
        
        self.ed_layout.addWidget(self.lbl_modulation)
        self.ed_layout.addWidget(self.lbl_snr)
        self.ed_layout.addWidget(self.lbl_confidence)
        self.ed_group.setLayout(self.ed_layout)

        # --- 2. ET (ELEKTRONİK TAARRUZ) KUTUSU ---
        self.et_group = QGroupBox("ELEKTRONİK TAARRUZ (ET)")
        self.et_group.setStyleSheet("QGroupBox { border: 1px solid #334155; margin-top: 15px; font-weight: bold; color: #ef4444; font-size: 13px; } QGroupBox::title { padding: 0 5px; }")
        self.et_layout = QVBoxLayout()
        self.et_layout.setSpacing(10)
        self.et_layout.setContentsMargins(15, 20, 15, 15)
        
        # Frekans Kaydırıcı (Slider)
        self.lbl_freq = QLabel("Hedef Frekans: 2400 MHz")
        self.lbl_freq.setStyleSheet("color: #e2e8f0; font-size: 13px; font-weight: bold; background: transparent; border: none;")
        
        self.slider_freq = QSlider(Qt.Orientation.Horizontal)
        self.slider_freq.setRange(400, 6000) # 400 MHz ile 6 GHz arası
        self.slider_freq.setValue(2400)
        self.slider_freq.valueChanged.connect(self.update_freq_label)
        
        # Karıştırma (Jamming) Tipi Seçimi
        self.lbl_type = QLabel("Karıştırma Tipi:")
        self.lbl_type.setStyleSheet("color: #94a3b8; font-size: 13px; background: transparent; border: none; margin-top: 10px;")
        
        self.combo_type = QComboBox()
        self.combo_type.addItems([
            "Akıllı Karıştırma (Spot Jamming)", 
            "Geniş Bant (Barrage Jamming)", 
            "Süpürme (Sweep Jamming)"
        ])
        
        # Kırmızı Taarruz Butonu
        self.btn_attack = QPushButton("TAARRUZU BAŞLAT")
        self.btn_attack.setCheckable(True) # Basılı kalabilen buton
        self.btn_attack.setFixedHeight(45)
        self.btn_attack.setStyleSheet("background-color: #ef4444; color: white; font-size: 15px; font-weight: bold; border-radius: 6px;")
        self.btn_attack.clicked.connect(self.toggle_attack)

        self.et_layout.addWidget(self.lbl_freq)
        self.et_layout.addWidget(self.slider_freq)
        self.et_layout.addWidget(self.lbl_type)
        self.et_layout.addWidget(self.combo_type)
        self.et_layout.addSpacing(15)
        self.et_layout.addWidget(self.btn_attack)
        self.et_group.setLayout(self.et_layout)

        # Kutuları Ana Panele Ekle
        self.layout.addWidget(self.ed_group)
        self.layout.addSpacing(10)
        self.layout.addWidget(self.et_group)
        self.layout.addStretch()

    def update_freq_label(self, value):
        self.lbl_freq.setText(f"Hedef Frekans: {value} MHz")

    def toggle_attack(self):
        """ Butona basıldığında rengini ve metnini değiştirir """
        if self.btn_attack.isChecked():
            self.btn_attack.setText("TAARRUZ AKTİF !!! [ DURDUR ]")
            self.btn_attack.setStyleSheet("background-color: #b91c1c; color: white; border: 2px solid #f87171; font-weight: bold; font-size: 15px; border-radius: 6px;")
        else:
            self.btn_attack.setText("TAARRUZU BAŞLAT")
            self.btn_attack.setStyleSheet("background-color: #ef4444; color: white; font-size: 15px; font-weight: bold; border-radius: 6px;")

    def update_ai_results(self, mod_type, snr, confidence):
        """ Yapay zekadan sonuç geldikçe ekrandaki yazıları günceller """
        self.lbl_modulation.setText(f"Hedef Sinyal: {mod_type}")
        self.lbl_snr.setText(f"Tahmini SNR: {snr} dB")
        self.lbl_confidence.setText(f"Yapay Zeka Güven Skoru: %{confidence}")
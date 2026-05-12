import sys
import numpy as np
import random
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, 
                             QVBoxLayout, QFrame, QLabel, QPushButton, QStackedWidget, QProgressBar)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from gui.components.panel_logs import SignalLogPanel # <--- BUNU EKLE
from gui.components.plot_waterfall import WaterfallAndIQPlot
from gui.components.panel_et import ControlPanel
from gui.components.panel_map import SignalMapPanel

# gui/main_window.py içinde şu satırı bul ve değiştir:
class MainWindow(QMainWindow):
    def __init__(self, buffer=None, state_manager=None): # <--- Parametreleri ekledik
        super().__init__()
        self.buffer = buffer
        self.state_manager = state_manager
        # ... geri kalan kodlar aynı ...
        
        self.setWindowTitle("Teknofest - Bilişsel Elektronik Harp Komuta Kontrol Arayüzü")
        self.resize(1366, 768)
        
        self.time_ptr = 0.0
        
        # --- ANA TEMA (Modern Dark UI / Slate) ---
        self.setStyleSheet("""
            QMainWindow { background-color: #0f172a; }
            QWidget { background-color: #0f172a; color: #f8fafc; font-family: 'Segoe UI', 'Inter', sans-serif; }
            QLabel { font-size: 14px; background-color: transparent; }
            QFrame { border: 1px solid #334155; border-radius: 12px; background-color: #1e293b; }
            QPushButton { 
                background-color: #3b82f6; border: none; color: white;
                padding: 10px; font-weight: bold; font-size: 14px; border-radius: 8px;
            }
            QPushButton:hover { background-color: #2563eb; }
            QPushButton:pressed { background-color: #1d4ed8; }
            QProgressBar { 
                border: none; border-radius: 6px; text-align: center; color: white; background-color: #334155;
            }
            QProgressBar::chunk { background-color: #10b981; border-radius: 6px; }
            QGroupBox { border: 1px solid #334155; border-radius: 12px; margin-top: 15px; padding-top: 15px; font-weight: bold; color: #94a3b8; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 10px; }
            QComboBox { background-color: #334155; color: #f8fafc; border: 1px solid #475569; border-radius: 6px; padding: 5px; }
            QComboBox::drop-down { border: none; }
            QSlider::groove:horizontal { border-radius: 4px; height: 8px; background: #334155; }
            QSlider::handle:horizontal { background: #3b82f6; width: 16px; height: 16px; margin: -4px 0; border-radius: 8px; }
        """)

        # Sayfaları üst üste koyacağımız yığın (Stack) yapısı
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        # Sayfaları Oluştur ve Yığına Ekle
        self.create_intro_screen()
        self.create_main_dashboard()
        
        self.stacked_widget.addWidget(self.intro_screen)
        self.stacked_widget.addWidget(self.main_dashboard)

        # --- CANLI TEST İÇİN SAHTE VERİ MOTORU (30ms periyod) ---
        self.active_signal_timer = 0
        self.active_signal_mod = ""
        self.active_signal_snr = 0.0
        self.active_signal_idx = 256

        self.timer = QTimer()
        self.timer.timeout.connect(self.simulate_live_data)
        self.timer.start(30) 

    def create_intro_screen(self):
        self.intro_screen = QWidget()
        self.intro_screen.setStyleSheet("QWidget { background-color: #f8fafc; color: #334155; font-family: 'Segoe UI', sans-serif; }")
        
        main_layout = QVBoxLayout(self.intro_screen)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ==========================================
        # 1. HEADER (ÜST BAR)
        # ==========================================
        header = QFrame()
        header.setFixedHeight(60)
        header.setStyleSheet("QFrame { background-color: #ffffff; border-bottom: 1px solid #e2e8f0; }")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 0, 20, 0)

        logo_label = QLabel("🛡️ <b>TEKNOFEST</b> BİLİŞSEL EH")
        logo_label.setStyleSheet("font-size: 20px; color: #0f172a; border: none; letter-spacing: 1px;")
        
        status_label = QLabel("🟢 SİSTEM BEKLEMEDE")
        status_label.setStyleSheet("font-size: 13px; color: #16a34a; font-weight: bold; border: none; padding: 5px 10px; background-color: #dcfce7; border-radius: 12px;")

        header_layout.addWidget(logo_label)
        header_layout.addStretch()
        header_layout.addWidget(status_label)

        # ==========================================
        # 2. ORTA ALAN (SOL BAR + ANA İÇERİK)
        # ==========================================
        content_area = QWidget()
        content_layout = QHBoxLayout(content_area)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # --- SOL BAR (SIDEBAR) ---
        sidebar = QFrame()
        sidebar.setFixedWidth(280)
        sidebar.setStyleSheet("QFrame { background-color: #ffffff; border-right: 1px solid #e2e8f0; }")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(25, 35, 25, 35)
        sidebar_layout.setSpacing(25)

        sys_info_title = QLabel("SİSTEM DURUMU")
        sys_info_title.setStyleSheet("font-size: 12px; font-weight: bold; color: #94a3b8; border: none; letter-spacing: 1px;")
        sidebar_layout.addWidget(sys_info_title)

        # Durum İndikatörleri
        def add_status_row(label_text, value_text, color):
            row = QWidget()
            row.setStyleSheet("border: none;")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0,0,0,0)
            lbl = QLabel(label_text)
            lbl.setStyleSheet("font-size: 14px; color: #475569; font-weight: 500;")
            val = QLabel(value_text)
            val.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {color};")
            row_layout.addWidget(lbl)
            row_layout.addStretch()
            row_layout.addWidget(val)
            sidebar_layout.addWidget(row)

        add_status_row("Yapay Zeka:", "PASİF", "#f59e0b") # Sarı
        add_status_row("SDR RX Portu:", "KAPALI", "#ef4444") # Kırmızı
        add_status_row("SDR TX Portu:", "KAPALI", "#ef4444") # Kırmızı
        
        sidebar_layout.addSpacing(10)
        
        # Donanım Barları
        def add_progress_bar(label_text, value):
            lbl = QLabel(label_text)
            lbl.setStyleSheet("font-size: 13px; color: #475569; font-weight: 500; border: none;")
            bar = QProgressBar()
            bar.setFixedHeight(8)
            bar.setValue(value)
            bar.setTextVisible(False)
            bar.setStyleSheet("""
                QProgressBar { border: none; background-color: #f1f5f9; border-radius: 4px; }
                QProgressBar::chunk { background-color: #3b82f6; border-radius: 4px; }
            """)
            sidebar_layout.addWidget(lbl)
            sidebar_layout.addWidget(bar)
            sidebar_layout.addSpacing(5)
            return bar

        self.ram_bar = add_progress_bar("Sistem Belleği (RAM)", 12)
        self.cpu_bar = add_progress_bar("İşlemci (CPU) Yükü", 4)
        self.net_bar = add_progress_bar("Ağ İletişimi", 0)

        # Barları gerçek zamanlı güncellemek için Timer
        self.intro_hardware_timer = QTimer(self.intro_screen)
        self.intro_hardware_timer.timeout.connect(self.update_hardware_bars)
        self.intro_hardware_timer.start(1000) # Saniyede bir güncelle

        sidebar_layout.addStretch()

        # --- ANA İÇERİK (SAĞ TARAF) ---
        main_content = QWidget()
        main_content_layout = QVBoxLayout(main_content)
        main_content_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_content_layout.setContentsMargins(40, 40, 40, 40)

        title = QLabel("Bilişsel Elektronik Harp\nKomuta Kontrol Sistemi")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                color: #0f172a; font-size: 46px; font-weight: 900;
                letter-spacing: -1px; border: none; line-height: 1.1;
            }
        """)

        subtitle = QLabel("Otonom Spektrum Hakimiyeti. Yeni Nesil Taarruz.")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #2563eb; font-size: 18px; font-weight: bold; letter-spacing: 2px; border: none;")

        description = QLabel(
            "<div style='text-align: center; line-height: 1.6;'>"
            "<p style='color: #475569; font-size: 17px;'>"
            "Savaş sahasındaki elektromanyetik spektrumu <b>1D-CNN ve Transformer</b><br>"
            "hibrit yapay zeka mimarisi ile gerçek zamanlı analiz edin. Düşman unsurlarına ait radyo<br>"
            "frekanslarını otonom olarak sınıflandırın ve hedef zafiyetine göre <b>Akıllı Karıştırma</b> uygulayın.</p></div>"
        )
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description.setStyleSheet("border: none; background: transparent;")

        # Özellik Kartları (Yanyana 3 Kutu)
        features_row = QHBoxLayout()
        features_row.setSpacing(25)
        features_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        def create_feature_box(icon, box_title, text):
            box = QFrame()
            box.setFixedSize(260, 160)
            box.setStyleSheet("""
                QFrame {
                    background-color: #ffffff; border: 1px solid #e2e8f0; 
                    border-radius: 12px;
                }
                QFrame:hover { border: 1px solid #cbd5e1; background-color: #f8fafc; }
            """)
            layout = QVBoxLayout(box)
            layout.setContentsMargins(20, 20, 20, 20)
            
            lbl_icon = QLabel(icon)
            lbl_icon.setStyleSheet("font-size: 28px; border: none;")
            
            lbl_title = QLabel(box_title)
            lbl_title.setStyleSheet("font-weight: 800; font-size: 15px; color: #0f172a; border: none;")
            
            lbl_text = QLabel(text)
            lbl_text.setWordWrap(True)
            lbl_text.setStyleSheet("font-size: 13px; color: #64748b; border: none; line-height: 1.4;")
            
            layout.addWidget(lbl_icon)
            layout.addSpacing(5)
            layout.addWidget(lbl_title)
            layout.addWidget(lbl_text)
            layout.addStretch()
            return box

        features_row.addWidget(create_feature_box("📡", "Gerçek Zamanlı IQ", "SDR üzerinden saniyede binlerce ham IQ paketini sıfır gecikme ile işleyin."))
        features_row.addWidget(create_feature_box("🧠", "Hibrit Yapay Zeka", "1D-CNN ve Attention modülleri ile çok düşük SNR değerlerinde bile yüksek isabet oranı sağlayın."))
        features_row.addWidget(create_feature_box("⚡", "Otonom Taarruz", "Hedef zafiyetine göre karıştırma (jamming) tipini belirleyip anında elektronik taarruz başlatın."))

        # Başlat Butonu
        start_btn = QPushButton("GÖREVİ BAŞLAT")
        start_btn.setFixedSize(300, 60)
        start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        start_btn.setStyleSheet("""
            QPushButton {
                background-color: #0f172a; color: #ffffff; font-size: 16px; font-weight: bold;
                letter-spacing: 2px; border: none; border-radius: 30px;
            }
            QPushButton:hover { background-color: #2563eb; }
            QPushButton:pressed { background-color: #1e3a8a; }
        """)
        start_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1))

        # Sağ Alanın Yerleşimi
        main_content_layout.addStretch()
        main_content_layout.addWidget(title)
        main_content_layout.addSpacing(10)
        main_content_layout.addWidget(subtitle)
        main_content_layout.addSpacing(25)
        main_content_layout.addWidget(description)
        main_content_layout.addSpacing(40)
        main_content_layout.addLayout(features_row)
        main_content_layout.addSpacing(50)
        main_content_layout.addWidget(start_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        main_content_layout.addStretch()

        # Sol bar ve sağ içeriği yan yana koy
        content_layout.addWidget(sidebar)
        content_layout.addWidget(main_content)

        # ==========================================
        # 3. FOOTER (ALT BAR)
        # ==========================================
        footer = QFrame()
        footer.setFixedHeight(45)
        footer.setStyleSheet("QFrame { background-color: #ffffff; border-top: 1px solid #e2e8f0; }")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(25, 0, 25, 0)
        
        footer_lbl_1 = QLabel("Sürüm: 1.0.0-beta")
        footer_lbl_1.setStyleSheet("font-size: 12px; color: #94a3b8; border: none; font-weight: 500;")
        footer_lbl_2 = QLabel("© 2026 Teknofest Bilişsel EH Takımı. Tüm Hakları Saklıdır.")
        footer_lbl_2.setStyleSheet("font-size: 12px; color: #94a3b8; border: none; font-weight: 500;")

        footer_layout.addWidget(footer_lbl_1)
        footer_layout.addStretch()
        footer_layout.addWidget(footer_lbl_2)

        # TÜM PARÇALARI ANA LAYOUTA EKLE
        main_layout.addWidget(header)
        main_layout.addWidget(content_area)
        main_layout.addWidget(footer)

    def update_hardware_bars(self):
        try:
            import psutil
            cpu_usage = int(psutil.cpu_percent())
            ram_usage = int(psutil.virtual_memory().percent)
            
            self.cpu_bar.setValue(cpu_usage)
            self.ram_bar.setValue(ram_usage)
            
            # Ağ trafiği için rastgele dalgalanma (Gerçek % hesaplamak anlık zor olduğu için aktivite simüle ediliyor)
            import random
            net_activity = random.randint(5, 35) 
            self.net_bar.setValue(net_activity)
            
        except ImportError:
            # Eğer bilgisayarda psutil kurulu değilse kod çökmesin diye rastgele değerler ata
            import random
            self.cpu_bar.setValue(random.randint(10, 30))
            self.ram_bar.setValue(random.randint(40, 60))
            self.net_bar.setValue(random.randint(5, 20))


    def create_main_dashboard(self):
        self.main_dashboard = QWidget()
        main_vbox = QVBoxLayout(self.main_dashboard)
        main_vbox.setContentsMargins(15, 15, 15, 15)
        main_vbox.setSpacing(15)

        panels_layout = QHBoxLayout()
        panels_layout.setSpacing(15)
        
        # 1. SOL PANEL (Sinyal Listesi)
        left_panel = QFrame()
        left_layout = QVBoxLayout(left_panel)
        
        # KENDİ YAZDIĞIMIZ LOG PANELİNİ BURAYA KOYUYORUZ
        self.log_panel_widget = SignalLogPanel()
        left_layout.addWidget(self.log_panel_widget)
        
        panels_layout.addWidget(left_panel, stretch=1)

# 2. ORTA PANEL (Harita ve Şelale Grafiği)
        middle_panel = QFrame()
        middle_layout = QVBoxLayout(middle_panel)
        
        # Üstte Harita
        self.map_widget = SignalMapPanel()
        middle_layout.addWidget(self.map_widget, stretch=2) # Harita alanı
        
        # Altta Şelale
        self.waterfall_widget = WaterfallAndIQPlot()
        middle_layout.addWidget(self.waterfall_widget, stretch=3) # Şelale alanı
        
        panels_layout.addWidget(middle_panel, stretch=4)
        # 3. SAĞ PANEL (AI ve ET Kontrol)
        right_panel = QFrame()
        right_layout = QVBoxLayout(right_panel)
        self.control_panel_widget = ControlPanel() # TAARRUZ PANELİ
        right_layout.addWidget(self.control_panel_widget)
        panels_layout.addWidget(right_panel, stretch=2)

        # Alt Kısım: Durum Çubuğu
        status_bar = QFrame()
        status_bar.setFixedHeight(45)
        status_bar.setStyleSheet("border-radius: 8px; background-color: #1e293b; border: 1px solid #334155;")
        status_layout = QHBoxLayout(status_bar)
        status_layout.setContentsMargins(15, 0, 15, 0)

        bat_label = QLabel("BATARYA: %85")
        bat_label.setStyleSheet("border: none; color: #10b981; font-weight: bold;")
        self.battery_bar = QProgressBar()
        self.battery_bar.setValue(85)
        self.battery_bar.setTextVisible(False) # Metin taşıyordu, etikete ekledik
        self.battery_bar.setFixedSize(150, 12)

        temp_label = QLabel("SİSTEM ISISI: 42°C")
        temp_label.setStyleSheet("border: none; color: #f59e0b; font-weight: bold;")
        
        system_status = QLabel("BAĞLANTI: SDR BEKLENİYOR...")
        system_status.setStyleSheet("border: none; color: #3b82f6; font-weight: bold;")

        status_layout.addWidget(bat_label)
        status_layout.addWidget(self.battery_bar)
        status_layout.addStretch()
        status_layout.addWidget(temp_label)
        status_layout.addStretch()
        status_layout.addWidget(system_status)

        main_vbox.addLayout(panels_layout, stretch=1)
        main_vbox.addWidget(status_bar)

    def simulate_live_data(self):
        """ SDR yokken arayüzü test etmek için sahte sinyal ve AI kararı üretir """
        # Sadece Dashboard sayfası (index 1) aktifken çizim yap
        if self.stacked_widget.currentIndex() == 1:
            
            # --- 1. Yapay Zeka (Panel) Simülasyonu ---
            # Ekranda sürekli değerler değişmesin diye %2 ihtimalle (ara sıra) yeni sinyal yakalıyoruz
            if random.random() < 0.02:
                fake_mods = ["BPSK", "QPSK", "8-PSK", "16-QAM", "64-QAM"]
                self.active_signal_mod = random.choice(fake_mods)
                self.active_signal_snr = round(random.uniform(5.0, 25.0), 1)
                conf = round(random.uniform(85.0, 99.9), 1)
                
                # Yeni hedefin frekans bandındaki yeri (512 bin üzerinden 50-460 arası)
                self.active_signal_idx = random.randint(50, 460)
                # Bu sinyali 50 frame (yaklaşık 1.5 saniye) boyunca ekranda aktif tut
                self.active_signal_timer = 50
                
                # Haritaya rastgele bir konuma hedef at (Örn: -8 ile +8 km arası)
                rx = random.uniform(-8, 8)
                ry = random.uniform(-8, 8)
                self.map_widget.add_target(rx, ry)
                
                # Sağ paneli güncelle
                self.control_panel_widget.update_ai_results(self.active_signal_mod, self.active_signal_snr, conf)
                
                # SOL PANELDEKİ LOGLARA YAZ!
                self.log_panel_widget.add_log(self.active_signal_mod, self.active_signal_snr, conf)

            # --- 2. Şelale (Waterfall) ve IQ Simülasyonu ---
            t = np.linspace(self.time_ptr, self.time_ptr + 10, 512)
            
            # Temel Gürültü (Noise Floor)
            noise = np.random.normal(0, 0.5, 512)
            fake_fft = np.random.uniform(0, 2, 512)
            
            # Eğer ekranda aktif bir tespit edilmiş sinyal varsa grafikleri ona göre çiz
            if self.active_signal_timer > 0:
                self.active_signal_timer -= 1
                
                # Genliği SNR ile orantılı yap
                amp = self.active_signal_snr / 10.0
                
                if "QAM" in self.active_signal_mod:
                    # QAM: Genlik (Amplitude) ve Faz aynı anda zıplamalı değişir
                    # 512 noktayı 32'lik paketlere (sembollere) bölelim
                    envelope = np.repeat(np.random.choice([0.3, 0.6, 1.0, 1.4], size=32), 16)
                    fake_iq = (envelope * amp) * np.sin(t * 5) + noise
                else:
                    # PSK: Genlik sabit, Faz zıplamalı değişir
                    phase_shifts = np.repeat(np.random.choice([0, np.pi/2, np.pi, 3*np.pi/2], size=32), 16)
                    fake_iq = amp * np.sin(t * 5 + phase_shifts) + noise

                # Şelale grafiğine sinyalin olduğu frekans bandında (idx) parlaklık (peak) ekle
                idx = self.active_signal_idx
                width = 8 if "QAM" in self.active_signal_mod else 4 # QAM daha geniş bant kaplar
                
                # FFT'de Peak (Zirve) oluştur
                fake_fft[idx-width : idx+width] += (self.active_signal_snr / 1.5)
                
            else:
                # Ekranda aktif sinyal yoksa sadece boş gürültü (Noise) aksın
                fake_iq = noise

            self.waterfall_widget.update_plots(fake_iq, fake_fft)
            self.time_ptr += 0.1
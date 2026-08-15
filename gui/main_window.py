import sys
import math
import numpy as np
import random
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout,
                             QVBoxLayout, QFrame, QLabel, QPushButton,
                             QStackedWidget, QProgressBar, QButtonGroup,
                             QSizePolicy)
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF
from PyQt6.QtGui import QFont, QPainter, QPen, QColor, QBrush, QLinearGradient, QPainterPath

from gui.components.panel_logs         import SignalLogPanel
from gui.components.plot_waterfall     import WaterfallAndIQPlot
from gui.components.panel_map          import SignalMapPanel
from gui.components.panel_taarruz     import TaarruzPanel
from gui.components.panel_arabakisli  import ArabakisliPanel
from gui.components.panel_telsiz_aldatma import TelsizAldatmaPanel
from gui.components.panel_gps_aldatma import GPSAldatmaPanel
from gui.components.panel_gns_aldatma import GNSAldatmaPanel
from gui.components.panel_df           import DirectionFinderPanel

try:
    import config
except ImportError:
    from .. import config


# ─────────────────────────────────────────────────────────────────────────────
#  TAKTİK HARİTA WİDGETI  (GNSS ekranı için)
# ─────────────────────────────────────────────────────────────────────────────
class _TacticalMap(QWidget):
    """Gerçek konum (mavi) ve sahte konum (kırmızı, yanıp söner) gösteren özel widget."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(260, 220)
        self._blink_on   = True
        self._blink_timer = QTimer(self)
        self._blink_timer.timeout.connect(self._blink)
        self._blink_timer.start(600)

        # Normalised koordinatlar [0..1, 0..1]
        self._real_pos  = QPointF(0.4, 0.5)
        self._fake_pos  = QPointF(0.65, 0.35)
        self._active    = False

    def set_positions(self, real_lat, real_lon, fake_lat, fake_lon):
        """Koordinatları basit doğrusal ölçekle normalize eder."""
        def norm(v, lo, hi): return max(0.05, min(0.95, (v - lo) / (hi - lo)))
        self._real_pos = QPointF(norm(real_lon, -180, 180), 1 - norm(real_lat, -90, 90))
        self._fake_pos = QPointF(norm(fake_lon, -180, 180), 1 - norm(fake_lat, -90, 90))
        self.repaint()

    def set_active(self, active: bool):
        self._active = active
        self.repaint()

    def wander_fake(self, step: float = 0.03):
        """Sahte konumu küçük rastgele adımlarla gezdirir (oynak konum simülasyonu)."""
        fx = min(0.9, max(0.1, self._fake_pos.x() + random.uniform(-step, step)))
        fy = min(0.9, max(0.1, self._fake_pos.y() + random.uniform(-step, step)))
        self._fake_pos = QPointF(fx, fy)
        self.repaint()

    def _blink(self):
        self._blink_on = not self._blink_on
        self.repaint()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Arka plan
        p.fillRect(0, 0, w, h, QColor("#0a0f1e"))

        # Grid çizgileri
        pen = QPen(QColor("#1e3a5f"), 1, Qt.PenStyle.DotLine)
        p.setPen(pen)
        for i in range(1, 5):
            x = int(w * i / 5)
            y = int(h * i / 5)
            p.drawLine(x, 0, x, h)
            p.drawLine(0, y, w, y)

        # Çevre çerçevesi
        p.setPen(QPen(QColor("#1e3a8a"), 1))
        p.drawRect(0, 0, w - 1, h - 1)

        rx = int(self._real_pos.x() * w)
        ry = int(self._real_pos.y() * h)
        fx = int(self._fake_pos.x() * w)
        fy = int(self._fake_pos.y() * h)

        # Kesik çizgi (gerçek → sahte)
        dash_pen = QPen(QColor("#334155"), 1, Qt.PenStyle.DashLine)
        p.setPen(dash_pen)
        p.drawLine(rx, ry, fx, fy)

        # Gerçek konum — mavi dolu daire
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#3b82f6")))
        p.drawEllipse(rx - 8, ry - 8, 16, 16)
        p.setPen(QPen(QColor("#93c5fd"), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(rx - 12, ry - 12, 24, 24)

        # Gerçek konum etiketi
        p.setPen(QPen(QColor("#93c5fd")))
        p.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        p.drawText(rx + 14, ry - 4, "GERÇEK")
        p.setFont(QFont("Consolas", 7))
        p.drawText(rx + 14, ry + 8,
                   f"({self._real_pos.x()*360-180:.1f}°, {(1-self._real_pos.y())*180-90:.1f}°)")

        # Sahte konum — kırmızı, yanıp söner
        if self._blink_on or not self._active:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor("#ef4444") if self._active else QColor("#7f1d1d")))
            p.drawEllipse(fx - 8, fy - 8, 16, 16)
            p.setPen(QPen(QColor("#fca5a5") if self._active else QColor("#b91c1c"), 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(fx - 14, fy - 14, 28, 28)

        # Sahte konum etiketi
        p.setPen(QPen(QColor("#fca5a5")))
        p.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        p.drawText(fx + 14, fy - 4, "SAHTE")
        p.setFont(QFont("Consolas", 7))
        p.drawText(fx + 14, fy + 8,
                   f"({self._fake_pos.x()*360-180:.1f}°, {(1-self._fake_pos.y())*180-90:.1f}°)")

        # Aktif durum rozeti
        status_txt = "● AKTİF" if self._active else "○ PASİF"
        status_col = "#00ff41" if self._active else "#475569"
        p.setPen(QPen(QColor(status_col)))
        p.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        p.drawText(6, 16, status_txt)

        p.end()


# ─────────────────────────────────────────────────────────────────────────────
#  ANA PENCERE
# ─────────────────────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self, buffer=None, state_manager=None):
        super().__init__()
        self.buffer        = buffer
        self.state_manager = state_manager

        self.setWindowTitle("Teknofest - Bilişsel Elektronik Harp Komuta Kontrol Arayüzü")
        self.resize(1440, 860)

        self.time_ptr = 0.0

        self.setStyleSheet("""
            QMainWindow { background-color: #0f172a; }
            QWidget { background-color: #0f172a; color: #f8fafc;
                      font-family: 'Segoe UI', 'Inter', sans-serif; }
            QLabel { font-size: 13px; background-color: transparent; }
            QFrame { border: 1px solid #334155; border-radius: 10px;
                     background-color: #1e293b; }
            QPushButton {
                background-color: #3b82f6; border: none; color: white;
                padding: 8px; font-weight: bold; font-size: 13px; border-radius: 7px;
            }
            QPushButton:hover { background-color: #2563eb; }
            QPushButton:pressed { background-color: #1d4ed8; }
            QProgressBar {
                border: none; border-radius: 5px; text-align: center;
                color: white; background-color: #334155;
            }
            QProgressBar::chunk { background-color: #10b981; border-radius: 5px; }
            QGroupBox {
                border: 1px solid #334155; border-radius: 10px;
                margin-top: 14px; padding-top: 14px; font-weight: bold; color: #94a3b8;
            }
            QGroupBox::title { subcontrol-origin: margin;
                               subcontrol-position: top left; padding: 0 8px; }
            QComboBox { background-color: #334155; color: #f8fafc;
                        border: 1px solid #475569; border-radius: 5px; padding: 4px; }
            QComboBox::drop-down { border: none; }
            QSlider::groove:horizontal { border-radius: 3px; height: 7px;
                                         background: #334155; }
            QSlider::handle:horizontal { background: #3b82f6; width: 15px;
                                         height: 15px; margin: -4px 0; border-radius: 7px; }
        """)

        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        self.create_intro_screen()       # index 0
        self.create_main_dashboard()     # index 1
        self.create_telsiz_screen()      # index 2
        self.create_gnss_screen()        # index 3

        self.stacked_widget.addWidget(self.intro_screen)
        self.stacked_widget.addWidget(self.main_dashboard)
        self.stacked_widget.addWidget(self.telsiz_screen)
        self.stacked_widget.addWidget(self.gnss_screen)

        self.active_signal_timer = 0
        self.active_signal_mod   = ""
        self.active_signal_snr   = 0.0
        self.active_signal_idx   = 256

        # Gerçek AI tespiti (state_manager) ile simülasyonu ayırt etmek için:
        # aynı tespiti tekrar tekrar loglamayalım diye son tespitin anahtarını tutuyoruz.
        self._last_detection_key = None

        # Yön Bulma (DF) simülasyonu: "gerçek" geliş açısı yavaş gezer (oynak),
        # ekrana gürültü eklenmiş hali basılır (RMS ~4°). Stabil değil — sahada olduğu gibi.
        self._true_bearing = random.uniform(0.0, 360.0)

        self.timer = QTimer()
        self.timer.timeout.connect(self.simulate_live_data)
        self.timer.start(30)

        # GNSS taktik haritasını state_manager'daki aldatma durumuna bağla
        # (GPS/GNSS panelleri start/stop'ta state_manager'ı günceller).
        self._gnss_timer = QTimer()
        self._gnss_timer.timeout.connect(self._update_tactical_map)
        self._gnss_timer.start(400)

    # ═══════════════════════════════════════════════════════════════════════
    #  NAVİGASYON ÇUBUĞU (ekranlar arası)
    # ═══════════════════════════════════════════════════════════════════════
    def _nav_bar(self, active_idx: int) -> QFrame:
        """3 ekranlı navigasyon çubuğu. active_idx: 1=Ana, 2=Telsiz, 3=GNSS"""
        bar = QFrame()
        bar.setFixedHeight(48)
        bar.setStyleSheet(
            "QFrame { background-color: #0a0f1e; border: none; border-radius: 0px; "
            "border-bottom: 2px solid #1e293b; }"
        )
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(0)

        # Geri butonu (intro ekranı)
        back_btn = QPushButton("◄  GİRİŞ")
        back_btn.setFixedSize(90, 32)
        back_btn.setStyleSheet(
            "QPushButton { background:#1e293b; color:#64748b; border:1px solid #334155; "
            "border-radius:6px; font-family:Consolas; font-size:9px; font-weight:bold; }"
            "QPushButton:hover { color:#94a3b8; border-color:#475569; }"
        )
        back_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        lay.addWidget(back_btn)
        lay.addSpacing(20)

        # Logo / başlık
        logo = QLabel("◈  BİLİŞSEL EH")
        logo.setStyleSheet(
            "color:#475569; font-family:Consolas; font-size:11px; font-weight:bold; "
            "border:none; background:transparent;"
        )
        lay.addWidget(logo)
        lay.addStretch()

        # Ekran butonları
        screens = [
            (1, "⚡  ANA EKRAN",       "#ef4444", "#7f1d1d"),
            (2, "📻  TELSİZ ALDATMA",  "#f97316", "#7c2d12"),
            (3, "🛰  GNSS ALDATMA",    "#8b5cf6", "#4c1d95"),
        ]
        for idx, label, col, dark in screens:
            btn = QPushButton(label)
            btn.setFixedHeight(32)
            btn.setMinimumWidth(160)
            btn.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
            if idx == active_idx:
                btn.setStyleSheet(
                    f"QPushButton {{ background:{dark}; color:{col}; border:2px solid {col}; "
                    f"border-radius:6px; padding:0 14px; }}"
                    f"QPushButton:hover {{ background:{dark}; }}"
                )
            else:
                btn.setStyleSheet(
                    "QPushButton { background:#1e293b; color:#475569; border:1px solid #334155; "
                    "border-radius:6px; padding:0 14px; }"
                    "QPushButton:hover { color:#94a3b8; border-color:#475569; }"
                )
            target = idx
            btn.clicked.connect(lambda checked, t=target: self.stacked_widget.setCurrentIndex(t))
            lay.addWidget(btn)
            if idx < 3:
                sep = QLabel("|")
                sep.setFixedWidth(18)
                sep.setAlignment(Qt.AlignmentFlag.AlignCenter)
                sep.setStyleSheet("color:#334155; border:none; background:transparent;")
                lay.addWidget(sep)

        lay.addStretch()

        # Saat / versiyon
        ver = QLabel("v1.0.0-beta")
        ver.setStyleSheet(
            "color:#334155; font-family:Consolas; font-size:9px; border:none; background:transparent;"
        )
        lay.addWidget(ver)

        return bar

    # ═══════════════════════════════════════════════════════════════════════
    #  GİRİŞ EKRANI  (index 0)
    # ═══════════════════════════════════════════════════════════════════════
    def create_intro_screen(self):
        self.intro_screen = QWidget()
        self.intro_screen.setStyleSheet(
            "QWidget { background-color: #f8fafc; color: #334155; "
            "font-family: 'Segoe UI', sans-serif; }"
        )

        main_layout = QVBoxLayout(self.intro_screen)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setFixedHeight(60)
        header.setStyleSheet("QFrame { background-color: #ffffff; border: none; "
                             "border-bottom: 1px solid #e2e8f0; border-radius: 0px; }")
        hlay = QHBoxLayout(header)
        hlay.setContentsMargins(20, 0, 20, 0)
        logo_lbl = QLabel("🛡️  <b>TEKNOFEST</b> BİLİŞSEL EH")
        logo_lbl.setStyleSheet("font-size: 20px; color: #0f172a; border: none;")
        status_lbl = QLabel("🟢 SİSTEM BEKLEMEDE")
        status_lbl.setStyleSheet(
            "font-size: 13px; color: #16a34a; font-weight: bold; border: none; "
            "padding: 5px 10px; background-color: #dcfce7; border-radius: 12px;"
        )
        hlay.addWidget(logo_lbl)
        hlay.addStretch()
        hlay.addWidget(status_lbl)

        # İçerik
        content_area   = QWidget()
        content_layout = QHBoxLayout(content_area)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Sidebar
        sidebar = QFrame()
        sidebar.setFixedWidth(280)
        sidebar.setStyleSheet(
            "QFrame { background-color: #ffffff; border: none; "
            "border-right: 1px solid #e2e8f0; border-radius: 0px; }"
        )
        slay = QVBoxLayout(sidebar)
        slay.setContentsMargins(25, 35, 25, 35)
        slay.setSpacing(20)

        sys_title = QLabel("SİSTEM DURUMU")
        sys_title.setStyleSheet(
            "font-size: 11px; font-weight: bold; color: #94a3b8; border: none; letter-spacing: 1px;"
        )
        slay.addWidget(sys_title)

        def add_status_row(lbl_txt, val_txt, color):
            row = QWidget()
            row.setStyleSheet("border: none;")
            rlay = QHBoxLayout(row)
            rlay.setContentsMargins(0, 0, 0, 0)
            lbl = QLabel(lbl_txt)
            lbl.setStyleSheet("font-size: 13px; color: #475569;")
            val = QLabel(val_txt)
            val.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {color};")
            rlay.addWidget(lbl)
            rlay.addStretch()
            rlay.addWidget(val)
            slay.addWidget(row)

        add_status_row("Yapay Zeka:",   "PASİF",  "#f59e0b")
        add_status_row("SDR RX Portu:", "KAPALI", "#ef4444")
        add_status_row("SDR TX Portu:", "KAPALI", "#ef4444")
        slay.addSpacing(10)

        def add_progress_bar(lbl_txt, value):
            lbl = QLabel(lbl_txt)
            lbl.setStyleSheet("font-size: 12px; color: #475569; border: none;")
            bar = QProgressBar()
            bar.setFixedHeight(8)
            bar.setValue(value)
            bar.setTextVisible(False)
            bar.setStyleSheet("""
                QProgressBar { border: none; background-color: #f1f5f9; border-radius: 4px; }
                QProgressBar::chunk { background-color: #3b82f6; border-radius: 4px; }
            """)
            slay.addWidget(lbl)
            slay.addWidget(bar)
            return bar

        self.ram_bar = add_progress_bar("Sistem Belleği (RAM)", 12)
        self.cpu_bar = add_progress_bar("İşlemci (CPU) Yükü",  4)
        self.net_bar = add_progress_bar("Ağ İletişimi",         0)

        self.intro_hardware_timer = QTimer(self.intro_screen)
        self.intro_hardware_timer.timeout.connect(self.update_hardware_bars)
        self.intro_hardware_timer.start(1000)

        slay.addStretch()

        # Sağ içerik
        main_content        = QWidget()
        main_content_layout = QVBoxLayout(main_content)
        main_content_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_content_layout.setContentsMargins(40, 40, 40, 40)

        title = QLabel("Bilişsel Elektronik Harp\nKomuta Kontrol Sistemi")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            "color: #0f172a; font-size: 44px; font-weight: 900; "
            "letter-spacing: -1px; border: none; line-height: 1.1;"
        )

        subtitle = QLabel("Otonom Spektrum Hakimiyeti. Yeni Nesil Taarruz.")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet(
            "color: #2563eb; font-size: 17px; font-weight: bold; "
            "letter-spacing: 2px; border: none;"
        )

        desc = QLabel(
            "<div style='text-align:center; line-height:1.6;'>"
            "<p style='color:#475569; font-size:16px;'>"
            "Savaş sahasındaki elektromanyetik spektrumu <b>1D-CNN ve Transformer</b><br>"
            "hibrit yapay zeka mimarisi ile gerçek zamanlı analiz edin. Düşman unsurlarına<br>"
            "ait radyo frekanslarını otonom olarak sınıflandırın ve <b>Akıllı Karıştırma</b> uygulayın."
            "</p></div>"
        )
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setStyleSheet("border: none; background: transparent;")

        # Özellik kartları
        feat_row = QHBoxLayout()
        feat_row.setSpacing(20)
        feat_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        def create_feat_box(icon, box_title, text):
            box = QFrame()
            box.setFixedSize(240, 150)
            box.setStyleSheet("""
                QFrame {
                    background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px;
                }
                QFrame:hover { border: 1px solid #cbd5e1; background-color: #f8fafc; }
            """)
            blay = QVBoxLayout(box)
            blay.setContentsMargins(18, 18, 18, 18)
            icon_lbl  = QLabel(icon)
            icon_lbl.setStyleSheet("font-size: 26px; border: none;")
            title_lbl = QLabel(box_title)
            title_lbl.setStyleSheet("font-weight: 800; font-size: 14px; color: #0f172a; border: none;")
            text_lbl  = QLabel(text)
            text_lbl.setWordWrap(True)
            text_lbl.setStyleSheet("font-size: 12px; color: #64748b; border: none;")
            blay.addWidget(icon_lbl)
            blay.addWidget(title_lbl)
            blay.addWidget(text_lbl)
            blay.addStretch()
            return box

        feat_row.addWidget(create_feat_box("📡", "Gerçek Zamanlı IQ",
            "SDR üzerinden saniyede binlerce ham IQ paketini işleyin."))
        feat_row.addWidget(create_feat_box("🧠", "Hibrit Yapay Zeka",
            "1D-CNN ve Attention modülleri ile yüksek SNR performansı."))
        feat_row.addWidget(create_feat_box("⚡", "Otonom Taarruz",
            "Hedef zafiyetine göre karıştırma / aldatma tipini belirle."))

        start_btn = QPushButton("GÖREVİ BAŞLAT")
        start_btn.setFixedSize(280, 56)
        start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        start_btn.setStyleSheet("""
            QPushButton {
                background-color: #0f172a; color: #ffffff; font-size: 15px;
                font-weight: bold; letter-spacing: 2px; border: none; border-radius: 28px;
            }
            QPushButton:hover { background-color: #2563eb; }
            QPushButton:pressed { background-color: #1e3a8a; }
        """)
        start_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1))

        main_content_layout.addStretch()
        main_content_layout.addWidget(title)
        main_content_layout.addSpacing(10)
        main_content_layout.addWidget(subtitle)
        main_content_layout.addSpacing(20)
        main_content_layout.addWidget(desc)
        main_content_layout.addSpacing(35)
        main_content_layout.addLayout(feat_row)
        main_content_layout.addSpacing(45)
        main_content_layout.addWidget(start_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        main_content_layout.addStretch()

        content_layout.addWidget(sidebar)
        content_layout.addWidget(main_content)

        # Footer
        footer = QFrame()
        footer.setFixedHeight(42)
        footer.setStyleSheet(
            "QFrame { background-color: #ffffff; border: none; "
            "border-top: 1px solid #e2e8f0; border-radius: 0px; }"
        )
        flay = QHBoxLayout(footer)
        flay.setContentsMargins(25, 0, 25, 0)
        f1 = QLabel("Sürüm: 1.0.0-beta")
        f1.setStyleSheet("font-size: 11px; color: #94a3b8; border: none;")
        f2 = QLabel("© 2026 Teknofest Bilişsel EH Takımı. Tüm Hakları Saklıdır.")
        f2.setStyleSheet("font-size: 11px; color: #94a3b8; border: none;")
        flay.addWidget(f1)
        flay.addStretch()
        flay.addWidget(f2)

        main_layout.addWidget(header)
        main_layout.addWidget(content_area)
        main_layout.addWidget(footer)

    def update_hardware_bars(self):
        try:
            import psutil
            self.cpu_bar.setValue(int(psutil.cpu_percent()))
            self.ram_bar.setValue(int(psutil.virtual_memory().percent))
            self.net_bar.setValue(random.randint(5, 35))
        except ImportError:
            self.cpu_bar.setValue(random.randint(10, 30))
            self.ram_bar.setValue(random.randint(40, 60))
            self.net_bar.setValue(random.randint(5, 20))

    # ═══════════════════════════════════════════════════════════════════════
    #  EKRAN 1  —  ANA EKRAN  (Destek + Taarruz)
    # ═══════════════════════════════════════════════════════════════════════
    def create_main_dashboard(self):
        self.main_dashboard = QWidget()
        root = QVBoxLayout(self.main_dashboard)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Navigasyon çubuğu
        root.addWidget(self._nav_bar(active_idx=1))

        # İçerik alanı
        content = QWidget()
        content_lay = QHBoxLayout(content)
        content_lay.setContentsMargins(10, 8, 10, 8)
        content_lay.setSpacing(10)

        # ── SOL: Sinyal Log Paneli ──────────────────────────────────────
        left_frame = QFrame()
        left_frame.setMinimumWidth(220)
        left_frame.setMaximumWidth(280)
        left_lay = QVBoxLayout(left_frame)
        left_lay.setContentsMargins(6, 6, 6, 6)
        left_lay.setSpacing(8)
        self.log_panel_widget = SignalLogPanel()
        self.df_panel = DirectionFinderPanel()
        left_lay.addWidget(self.log_panel_widget, stretch=1)
        left_lay.addWidget(self.df_panel)
        content_lay.addWidget(left_frame)

        # ── ORTA: Harita + Waterfall ─────────────────────────────────
        mid_frame = QFrame()
        mid_lay   = QVBoxLayout(mid_frame)
        mid_lay.setContentsMargins(6, 6, 6, 6)
        mid_lay.setSpacing(8)
        self.map_widget       = SignalMapPanel()
        self.waterfall_widget = WaterfallAndIQPlot()
        mid_lay.addWidget(self.map_widget,       stretch=2)
        mid_lay.addWidget(self.waterfall_widget, stretch=3)
        content_lay.addWidget(mid_frame, stretch=1)

        # ── SAĞ: Taarruz alt-panel (sub-toggle) ─────────────────────
        right_frame = QFrame()
        right_frame.setMinimumWidth(300)
        right_frame.setMaximumWidth(380)
        right_lay   = QVBoxLayout(right_frame)
        right_lay.setContentsMargins(8, 8, 8, 8)
        right_lay.setSpacing(8)

        # Alt-toggle: SÜREKLİ | ARABAKIŞLI
        toggle_bar = QFrame()
        toggle_bar.setFixedHeight(38)
        toggle_bar.setStyleSheet(
            "QFrame { background-color: #0f172a; border: 1px solid #1e293b; "
            "border-radius: 8px; }"
        )
        toggle_lay = QHBoxLayout(toggle_bar)
        toggle_lay.setContentsMargins(6, 4, 6, 4)
        toggle_lay.setSpacing(6)

        self._atk_btn_group = QButtonGroup(self)

        self._btn_surekli = QPushButton("⚡  SÜREKLİ KARIŞTIRMA")
        self._btn_surekli.setCheckable(True)
        self._btn_surekli.setChecked(True)
        self._btn_surekli.setFixedHeight(28)
        self._btn_surekli.setFont(QFont("Consolas", 8, QFont.Weight.Bold))

        self._btn_arabakisli = QPushButton("🔄  ARABAKIŞLI KARIŞTIRMA")
        self._btn_arabakisli.setCheckable(True)
        self._btn_arabakisli.setFixedHeight(28)
        self._btn_arabakisli.setFont(QFont("Consolas", 8, QFont.Weight.Bold))

        self._atk_btn_group.addButton(self._btn_surekli,    0)
        self._atk_btn_group.addButton(self._btn_arabakisli, 1)

        toggle_lay.addWidget(self._btn_surekli)
        toggle_lay.addWidget(self._btn_arabakisli)

        self._apply_atk_toggle(0)
        self._atk_btn_group.idToggled.connect(
            lambda bid, checked: self._on_atk_toggle(bid) if checked else None
        )

        right_lay.addWidget(toggle_bar)

        # Alt-panel stack
        self._atk_stack = QStackedWidget()

        self.control_panel_widget = TaarruzPanel(state_manager=self.state_manager)
        self.arabakisli_panel     = ArabakisliPanel(state_manager=self.state_manager)

        self._atk_stack.addWidget(self.control_panel_widget)  # 0
        self._atk_stack.addWidget(self.arabakisli_panel)       # 1

        right_lay.addWidget(self._atk_stack, stretch=1)
        content_lay.addWidget(right_frame)

        root.addWidget(content, stretch=1)

        # Alt durum çubuğu
        root.addWidget(self._build_status_bar())

    def _apply_atk_toggle(self, active_id: int):
        active_styles = {
            0: ("QPushButton { background:#7f1d1d; color:#ef4444; border:2px solid #ef4444; "
                "border-radius:6px; padding:0 8px; }"
                "QPushButton:hover { background:#7f1d1d; }"),
            1: ("QPushButton { background:#0c2a33; color:#00d4ff; border:2px solid #00d4ff; "
                "border-radius:6px; padding:0 8px; }"
                "QPushButton:hover { background:#0c2a33; }"),
        }
        inactive = ("QPushButton { background:#1e293b; color:#475569; border:1px solid #334155; "
                    "border-radius:6px; padding:0 8px; }"
                    "QPushButton:hover { color:#94a3b8; }")
        self._btn_surekli.setStyleSheet(
            active_styles[0] if active_id == 0 else inactive
        )
        self._btn_arabakisli.setStyleSheet(
            active_styles[1] if active_id == 1 else inactive
        )

    def _on_atk_toggle(self, bid: int):
        self._atk_stack.setCurrentIndex(bid)
        self._apply_atk_toggle(bid)

    def _build_status_bar(self) -> QFrame:
        bar = QFrame()
        bar.setFixedHeight(38)
        bar.setStyleSheet(
            "QFrame { border-radius: 0px; background-color: #0a0f1e; "
            "border: none; border-top: 1px solid #1e293b; }"
        )
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(16, 0, 16, 0)

        bat_lbl = QLabel("BATARYA: %85")
        bat_lbl.setStyleSheet("border: none; color: #10b981; font-weight: bold; font-size: 12px;")
        self.battery_bar = QProgressBar()
        self.battery_bar.setValue(85)
        self.battery_bar.setTextVisible(False)
        self.battery_bar.setFixedSize(120, 10)

        temp_lbl = QLabel("ISI: 42°C")
        temp_lbl.setStyleSheet("border: none; color: #f59e0b; font-weight: bold; font-size: 12px;")

        conn_lbl = QLabel("BAĞLANTI: SDR BEKLENİYOR...")
        conn_lbl.setStyleSheet("border: none; color: #3b82f6; font-weight: bold; font-size: 12px;")

        self._mission_status_lbl = QLabel("EKRAN: ANA EKRAN")
        self._mission_status_lbl.setStyleSheet(
            "border: none; color: #ef4444; font-weight: bold; font-family: Consolas; font-size: 12px;"
        )

        lay.addWidget(bat_lbl)
        lay.addWidget(self.battery_bar)
        lay.addStretch()
        lay.addWidget(self._mission_status_lbl)
        lay.addStretch()
        lay.addWidget(temp_lbl)
        lay.addStretch()
        lay.addWidget(conn_lbl)
        return bar

    # ═══════════════════════════════════════════════════════════════════════
    #  EKRAN 2  —  TELSİZ ALDATMA  (Tam ekran)
    # ═══════════════════════════════════════════════════════════════════════
    def create_telsiz_screen(self):
        self.telsiz_screen = QWidget()
        root = QVBoxLayout(self.telsiz_screen)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._nav_bar(active_idx=2))

        # Tam ekran TelsizAldatmaPanel
        wrapper = QWidget()
        wlay = QHBoxLayout(wrapper)
        wlay.setContentsMargins(10, 8, 10, 8)
        self.telsiz_panel = TelsizAldatmaPanel(state_manager=self.state_manager)
        wlay.addWidget(self.telsiz_panel)
        root.addWidget(wrapper, stretch=1)

        # Alt durum çubuğu
        status = QFrame()
        status.setFixedHeight(38)
        status.setStyleSheet(
            "QFrame { border-radius:0px; background-color:#0a0f1e; "
            "border:none; border-top:1px solid #1e293b; }"
        )
        slay = QHBoxLayout(status)
        slay.setContentsMargins(16, 0, 16, 0)
        ekran_lbl = QLabel("EKRAN: TELSİZ ALDATMA")
        ekran_lbl.setStyleSheet(
            "border:none; color:#f97316; font-weight:bold; font-family:Consolas; font-size:12px;"
        )
        slay.addStretch()
        slay.addWidget(ekran_lbl)
        slay.addStretch()
        root.addWidget(status)

    # ═══════════════════════════════════════════════════════════════════════
    #  EKRAN 3  —  GNSS ALDATMA  (Tam ekran)
    # ═══════════════════════════════════════════════════════════════════════
    def create_gnss_screen(self):
        self.gnss_screen = QWidget()
        root = QVBoxLayout(self.gnss_screen)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._nav_bar(active_idx=3))

        # İçerik: 3 sütun
        content = QWidget()
        clay = QHBoxLayout(content)
        clay.setContentsMargins(10, 8, 10, 8)
        clay.setSpacing(10)

        # ── SOL SÜTUN: GPS + GNS Konstelasyon panelleri ──────────────
        left_col = QWidget()
        left_col.setMaximumWidth(380)
        left_col.setMinimumWidth(300)
        lcol_lay = QVBoxLayout(left_col)
        lcol_lay.setContentsMargins(0, 0, 0, 0)
        lcol_lay.setSpacing(8)

        gps_frame = QFrame()
        gps_lay = QVBoxLayout(gps_frame)
        gps_lay.setContentsMargins(6, 6, 6, 6)
        self.gps_panel = GPSAldatmaPanel(state_manager=self.state_manager)
        gps_lay.addWidget(self.gps_panel)
        lcol_lay.addWidget(gps_frame, stretch=1)

        clay.addWidget(left_col)

        # ── ORTA SÜTUN: Taktik harita + GNS paneli ──────────────────
        mid_col = QWidget()
        mcol_lay = QVBoxLayout(mid_col)
        mcol_lay.setContentsMargins(0, 0, 0, 0)
        mcol_lay.setSpacing(8)

        # Taktik harita kartı
        map_frame = QFrame()
        map_frame.setMinimumHeight(220)
        map_frame_lay = QVBoxLayout(map_frame)
        map_frame_lay.setContentsMargins(6, 6, 6, 6)

        map_title = QLabel("TAKTİK KONUMLandırma HARİTASI")
        map_title.setStyleSheet(
            "color:#8b5cf6; font-family:Consolas; font-size:10px; font-weight:bold; "
            "border:none; background:transparent; letter-spacing:1px;"
        )
        self.tactical_map = _TacticalMap()
        map_frame_lay.addWidget(map_title)
        map_frame_lay.addWidget(self.tactical_map, stretch=1)
        mcol_lay.addWidget(map_frame, stretch=1)

        gns_frame = QFrame()
        gns_lay = QVBoxLayout(gns_frame)
        gns_lay.setContentsMargins(6, 6, 6, 6)
        self.gns_panel = GNSAldatmaPanel(state_manager=self.state_manager)
        gns_lay.addWidget(self.gns_panel)
        mcol_lay.addWidget(gns_frame, stretch=2)

        clay.addWidget(mid_col, stretch=1)

        # ── SAĞ SÜTUN: Özet ve bilgi paneli ─────────────────────────
        right_col = QFrame()
        right_col.setMinimumWidth(220)
        right_col.setMaximumWidth(280)
        rcol_lay = QVBoxLayout(right_col)
        rcol_lay.setContentsMargins(12, 12, 12, 12)
        rcol_lay.setSpacing(12)

        info_title = QLabel("GNSS ALDATMA BİLGİLERİ")
        info_title.setStyleSheet(
            "color:#8b5cf6; font-family:Consolas; font-size:10px; font-weight:bold; "
            "border:none; letter-spacing:1px;"
        )
        rcol_lay.addWidget(info_title)

        def info_row(label, value, color="#94a3b8"):
            row = QWidget()
            row.setStyleSheet("background:transparent; border:none;")
            rlay = QHBoxLayout(row)
            rlay.setContentsMargins(0, 0, 0, 0)
            lbl = QLabel(label)
            lbl.setStyleSheet("color:#64748b; font-size:11px; border:none; background:transparent;")
            val = QLabel(value)
            val.setStyleSheet(
                f"color:{color}; font-size:11px; font-weight:bold; font-family:Consolas; "
                "border:none; background:transparent;"
            )
            rlay.addWidget(lbl)
            rlay.addStretch()
            rlay.addWidget(val)
            return row

        rcol_lay.addWidget(info_row("Mod:",        "GPS + GNSS",  "#8b5cf6"))
        rcol_lay.addWidget(info_row("TX Gücü:",    "30 dBm",      "#f97316"))
        rcol_lay.addWidget(info_row("Frekans:",    "1575.42 MHz", "#3b82f6"))
        rcol_lay.addWidget(info_row("PRN Sayısı:", "8",           "#10b981"))
        rcol_lay.addWidget(info_row("Durum:",      "PASİF",       "#475569"))

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("QFrame { background:#334155; border:none; border-radius:0px; }")
        rcol_lay.addWidget(sep)

        warn_lbl = QLabel(
            "⚠  UYARI\n\nGNSS aldatma sinyali\nyalnızca yetkili\ntest sahasında\nkullanılabilir."
        )
        warn_lbl.setWordWrap(True)
        warn_lbl.setStyleSheet(
            "color:#f59e0b; font-size:11px; font-family:Consolas; border:none; "
            "background:transparent; line-height:1.5;"
        )
        rcol_lay.addWidget(warn_lbl)
        rcol_lay.addStretch()

        clay.addWidget(right_col)

        root.addWidget(content, stretch=1)

        # Alt durum çubuğu
        status = QFrame()
        status.setFixedHeight(38)
        status.setStyleSheet(
            "QFrame { border-radius:0px; background-color:#0a0f1e; "
            "border:none; border-top:1px solid #1e293b; }"
        )
        slay = QHBoxLayout(status)
        slay.setContentsMargins(16, 0, 16, 0)
        ekran_lbl = QLabel("EKRAN: GNSS ALDATMA")
        ekran_lbl.setStyleSheet(
            "border:none; color:#8b5cf6; font-weight:bold; font-family:Consolas; font-size:12px;"
        )
        slay.addStretch()
        slay.addWidget(ekran_lbl)
        slay.addStretch()
        root.addWidget(status)

    # ═══════════════════════════════════════════════════════════════════════
    #  SİMÜLASYON
    # ═══════════════════════════════════════════════════════════════════════
    def _trigger_detection(self, mod: str, snr: float, conf: float, peak_bin=None):
        """Yeni bir sinyal tespitini işler: paneller + log + harita + waterfall zarfı."""
        self.active_signal_mod   = mod
        self.active_signal_snr   = snr
        # Frekans konumu: gerçek tespit varsa FFT tepesinin bin indeksi, yoksa
        # (sadece simülasyon modunda) rastgele. Eskiden her zaman rastgeleydi —
        # gerçek sinyal gelse bile waterfall'daki yer uydurma çıkıyordu.
        self.active_signal_idx   = (int(peak_bin) if peak_bin is not None
                                    else random.randint(50, 460))
        self.active_signal_timer = 50

        # Yeni sinyal yeni bir yönden geliyor gibi davran (oynak yön)
        self._true_bearing = random.uniform(0.0, 360.0)

        rx, ry = random.uniform(-8, 8), random.uniform(-8, 8)
        self.map_widget.add_target(rx, ry)

        self.control_panel_widget.update_ai_results(mod, snr, conf)
        self.log_panel_widget.add_log(mod, snr, conf)

    def _get_real_detection(self):
        """state_manager'da gerçek AI tespiti varsa (mod, snr, conf) döndürür, yoksa None.

        main.py çalıştığında InferenceEngine thread'i state_manager'a yazar. GUI tek
        başına (AI thread'siz) açılırsa state varsayılanda kalır ve None döner -> sim.
        """
        if self.state_manager is None:
            return None
        try:
            st = self.state_manager.get_state()
        except Exception:
            return None
        mod = st.get("mod")
        if not mod or mod in ("Bekleniyor...", "ARANIYOR...", "SİNYAL YOK", ""):
            return None
        # Spektrumda sinyal yoksa tespit de yok say
        if not st.get("signal_present", False):
            return None
        return (mod, float(st.get("snr", 0.0)), float(st.get("conf", 0.0)),
                st.get("peak_bin"), float(st.get("detected_freq_hz", 0.0)))

    def _update_tactical_map(self):
        """GNSS taktik haritasını state_manager'daki GPS/GNSS aldatma durumuna bağlar."""
        if self.state_manager is None:
            return
        try:
            st = self.state_manager.get_state()
        except Exception:
            return
        active = bool(st.get("gps_active") or st.get("gns_active"))
        self.tactical_map.set_active(active)
        # Aldatma aktifken sahte konum gerçekçi biçimde gezsin (oynak konum)
        if active:
            self.tactical_map.wander_fake()

    def _get_live_spectrum(self):
        """SDR'dan gelen gerçek (IQ, FFT) çiftini döndürür, veri yoksa None."""
        if self.state_manager is None or self.buffer is None:
            return None
        try:
            st = self.state_manager.get_state()
        except Exception:
            return None
        if not st.get("has_live_data"):
            return None

        psd = st.get("spectrum_db")
        # peek_latest: AI motorunun kuyruğunu tüketmeden en son segmenti oku
        iq = self.buffer.peek_latest()
        if psd is None or iq is None:
            return None

        # dB spektrumu waterfall'ın 0-10 renk aralığına taşı (gürültü tabanı = 0)
        floor = float(st.get("noise_floor", np.median(psd)))
        fft_disp = np.clip((np.asarray(psd) - floor) / 3.0, 0.0, 10.0)

        # IQ eğrisi: I kanalı, ±3 aralığına sığsın diye normalize
        i_ch = np.asarray(iq)[0][:512]
        peak = np.max(np.abs(i_ch))
        if peak > 1e-9:
            i_ch = i_ch / peak * 2.5
        return i_ch, fft_disp

    def simulate_live_data(self):
        if self.stacked_widget.currentIndex() != 1:
            return

        # 1) ÖNCELİK: state_manager'daki gerçek AI tespiti.
        real = self._get_real_detection()
        if real is not None:
            mod, snr, conf, peak_bin, freq_hz = real
            key = (mod, round(conf, 1), round(snr, 1), peak_bin)
            if key != self._last_detection_key:   # sadece yeni/değişen tespitte tetikle
                self._last_detection_key = key
                self._trigger_detection(mod, snr, conf, peak_bin=peak_bin)
        elif config.SIMULATION_MODE and random.random() < 0.02:
            # SADECE simülasyon modunda (config.SIMULATION_MODE = True).
            # Sahada bu kapalıdır: sinyal gelmeden ekranda tespit BELİRMEZ.
            fake_mods = ["BPSK", "QPSK", "8PSK", "16QAM", "64QAM"]
            self._trigger_detection(
                random.choice(fake_mods),
                round(random.uniform(5.0, 25.0), 1),
                round(random.uniform(85.0, 99.9), 1),
            )

        # 2) SPEKTRUM: gerçek SDR verisi varsa onu çiz.
        live = self._get_live_spectrum()
        if live is not None:
            real_iq, real_fft = live
            self.waterfall_widget.update_plots(real_iq, real_fft)
            if self.active_signal_timer > 0:
                self.active_signal_timer -= 1
                self._true_bearing = (self._true_bearing + random.uniform(-1.5, 1.5)) % 360
                shown = (self._true_bearing + random.gauss(0.0, 4.0)) % 360
                self.df_panel.update_bearing(
                    shown, 4.0, self.active_signal_mod, self.active_signal_snr
                )
            else:
                self.df_panel.set_scanning(True)
            self.time_ptr += 0.1
            return

        # 3) Gerçek veri yok. Simülasyon kapalıysa ekranı BOŞ/sessiz tut —
        #    açılışta uydurma dalga akmasın diye.
        if not config.SIMULATION_MODE:
            self.waterfall_widget.update_plots(np.zeros(512), np.zeros(512))
            self.df_panel.set_scanning(True)
            return

        t     = np.linspace(self.time_ptr, self.time_ptr + 10, 512)
        noise = np.random.normal(0, 0.5, 512)
        fake_fft = np.random.uniform(0, 2, 512)

        if self.active_signal_timer > 0:
            self.active_signal_timer -= 1
            amp = self.active_signal_snr / 10.0
            if "QAM" in self.active_signal_mod:
                envelope = np.repeat(np.random.choice([0.3, 0.6, 1.0, 1.4], size=32), 16)
                fake_iq  = (envelope * amp) * np.sin(t * 5) + noise
            else:
                phase_shifts = np.repeat(
                    np.random.choice([0, np.pi / 2, np.pi, 3 * np.pi / 2], size=32), 16
                )
                fake_iq = amp * np.sin(t * 5 + phase_shifts) + noise

            idx   = self.active_signal_idx
            width = 8 if "QAM" in self.active_signal_mod else 4
            fake_fft[idx - width: idx + width] += self.active_signal_snr / 1.5

            # Yön Bulma: gerçek açı yavaşça gezsin, ekrana gürültülü (RMS~4°) hali bas
            self._true_bearing = (self._true_bearing + random.uniform(-1.5, 1.5)) % 360
            shown = (self._true_bearing + random.gauss(0.0, 4.0)) % 360
            self.df_panel.update_bearing(
                shown, 4.0, self.active_signal_mod, self.active_signal_snr
            )
        else:
            fake_iq = noise
            # Aktif sinyal yoksa DF tarama modunda
            self.df_panel.set_scanning(True)

        self.waterfall_widget.update_plots(fake_iq, fake_fft)
        self.time_ptr += 0.1

"""
Elektronik Taarruz (ET) Kontrol Paneli
panel_et.py'nin geliştirilmiş versiyonu — askeri mod seçici, AI öneri, güç kontrolü
"""

import math
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QGroupBox, QButtonGroup, QFrame,
)
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QFont, QFontMetrics, QLinearGradient

# ─── AI önerisi tablosu (modülasyon → karıştırma tekniği) ────────────────────
AI_RECS = {
    "BPSK":   "Faz Bozma",
    "QPSK":   "Faz Bozma",
    "8-PSK":  "Çok Tonlu Karıştırma",
    "16-QAM": "Gürültü Enjeksiyonu",
    "64-QAM": "Alt Taşıyıcı Baskı",
    "AM":     "Genlik Baskılama",
    "FM":     "Frekans Kayması",
    "FSK":    "Frekans Atlama Takibi",
    "OFDM":   "Alt Taşıyıcı Baskı",
}


# ─── Mini gauge (yay tabanlı etkinlik göstergesi) ────────────────────────────
class _MiniGauge(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._val    = 0.0
        self._target = 0.0
        self.setFixedHeight(110)
        t = QTimer(self)
        t.timeout.connect(self._step)
        t.start(30)

    def set_value(self, v: float):
        self._target = max(0.0, min(100.0, v))

    def _step(self):
        d = self._target - self._val
        if abs(d) > 0.3:
            self._val += d * 0.12
            self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("#1e293b"))

        cx, cy = self.width() // 2, int(self.height() * 0.78)
        r = min(self.width(), int(self.height() * 1.4)) // 2 - 10

        arc = QRectF(cx - r, cy - r, 2 * r, 2 * r)
        START, SPAN = 210, 120

        # Arka yay
        p.setPen(QPen(QColor("#334155"), 7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawArc(arc, int(START * 16), int(-SPAN * 16))

        # Değer yayı
        frac = self._val / 100.0
        if frac > 0:
            if frac < 0.5:
                rc, gc = int(255 * frac / 0.5), 255
            else:
                rc, gc = 255, int(255 * (1 - (frac - 0.5) / 0.5))
            p.setPen(QPen(QColor(rc, gc, 0), 7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawArc(arc, int(START * 16), int(-SPAN * frac * 16))

        # İbre
        ang = math.radians(START - SPAN * frac)
        nx, ny = cx + (r - 5) * math.cos(ang), cy - (r - 5) * math.sin(ang)
        p.setPen(QPen(QColor("#f8fafc"), 2))
        p.drawLine(QPointF(cx, cy), QPointF(nx, ny))
        p.setBrush(QBrush(QColor("#475569")))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(cx, cy), 4, 4)

        # Sayısal değer
        lbl = f"{int(self._val)}%"
        p.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
        fm  = QFontMetrics(QFont("Consolas", 11, QFont.Weight.Bold))
        col = QColor("#10b981") if self._val >= 50 else QColor("#f59e0b")
        p.setPen(QPen(col))
        p.drawText(cx - fm.horizontalAdvance(lbl) // 2, cy + 18, lbl)

        # Başlık
        title = "ETKİNLİK"
        p.setFont(QFont("Consolas", 7))
        p.setPen(QPen(QColor("#64748b")))
        fm2 = QFontMetrics(QFont("Consolas", 7))
        p.drawText(cx - fm2.horizontalAdvance(title) // 2, 12, title)
        p.end()


# ─── Dikey güç barı ──────────────────────────────────────────────────────────
class _PowerBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._level = 0.0
        self.setFixedWidth(22)

    def set_level(self, w: float):
        self._level = w
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#1e293b"))
        pad = 4
        bh = self.height() - 2 * pad
        bw = self.width()  - 2 * pad
        p.fillRect(pad, pad, bw, bh, QColor("#334155"))
        frac = self._level / 5.0
        fh = int(bh * frac)
        if fh > 0:
            grad = QLinearGradient(0, pad + bh, 0, pad + bh - fh)
            grad.setColorAt(0.0, QColor("#10b981"))
            grad.setColorAt(0.6, QColor("#f59e0b"))
            grad.setColorAt(1.0, QColor("#ef4444"))
            p.fillRect(pad, pad + bh - fh, bw, fh, QBrush(grad))
        p.end()


# ─── Ana Taarruz Paneli ───────────────────────────────────────────────────────
class TaarruzPanel(QWidget):
    """
    Mevcut ControlPanel'in geliştirilmiş versiyonu.
    update_ai_results() metodu korundu — main_window.py ile uyumlu.
    """

    def __init__(self, state_manager=None):
        super().__init__()
        self.state_manager = state_manager
        self._jam_active   = False
        self._power_w      = 0.0
        self._effectiveness = 0.0

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        # ── 1. ED Durum Kutusu ──────────────────────────────────────────
        ed_box = QGroupBox("BİLİŞSEL ED DURUMU")
        ed_box.setStyleSheet(self._gbox_style("#3b82f6"))
        ed_lay = QVBoxLayout(ed_box)
        ed_lay.setContentsMargins(12, 18, 12, 12)
        ed_lay.setSpacing(6)

        self.lbl_modulation  = QLabel("Hedef Sinyal: ARANIYOR...")
        self.lbl_snr         = QLabel("Tahmini SNR: -- dB")
        self.lbl_confidence  = QLabel("Yapay Zeka Güven Skoru: %0")
        self._ai_rec_lbl     = QLabel("AI Öneri: ---")

        self.lbl_modulation.setStyleSheet("color:#f8fafc; font-size:14px; font-weight:bold; border:none; background:transparent;")
        for lbl in [self.lbl_snr, self.lbl_confidence]:
            lbl.setStyleSheet("color:#94a3b8; font-size:12px; border:none; background:transparent;")
        self._ai_rec_lbl.setStyleSheet(
            "color:#10b981; font-size:12px; font-weight:bold; border:1px solid #065f46; "
            "border-radius:4px; padding:3px 6px; background:#022c22;"
        )

        ed_lay.addWidget(self.lbl_modulation)
        ed_lay.addWidget(self.lbl_snr)
        ed_lay.addWidget(self.lbl_confidence)
        ed_lay.addWidget(self._ai_rec_lbl)
        root.addWidget(ed_box)

        # ── 2. Karıştırma Modu ──────────────────────────────────────────
        mode_box = QGroupBox("KARIŞTIRMA MODU")
        mode_box.setStyleSheet(self._gbox_style("#ef4444"))
        mode_lay = QHBoxLayout(mode_box)
        mode_lay.setContentsMargins(10, 18, 10, 10)
        mode_lay.setSpacing(6)

        self._mode_group = QButtonGroup(self)
        self._mode_btns  = {}
        for i, label in enumerate(["TEKLİ", "ÇOKLU", "BARAJ"]):
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
            btn.setFixedHeight(32)
            self._mode_group.addButton(btn, i)
            self._mode_btns[i] = btn
            mode_lay.addWidget(btn)

        self._mode_btns[0].setChecked(True)
        self._refresh_mode_styles(0)
        self._mode_group.idToggled.connect(
            lambda bid, checked: self._refresh_mode_styles(bid) if checked else None
        )
        root.addWidget(mode_box)

        # ── 3. Güç Kontrolü ─────────────────────────────────────────────
        pwr_box = QGroupBox("GÜÇ AYARI (0 – 5 W)")
        pwr_box.setStyleSheet(self._gbox_style("#f59e0b"))
        pwr_lay = QHBoxLayout(pwr_box)
        pwr_lay.setContentsMargins(10, 18, 10, 10)
        pwr_lay.setSpacing(8)

        self._pwr_slider = QSlider(Qt.Orientation.Vertical)
        self._pwr_slider.setRange(0, 50)
        self._pwr_slider.setValue(0)
        self._pwr_slider.setFixedHeight(80)
        self._pwr_slider.setStyleSheet("""
            QSlider::groove:vertical {
                width:8px; background:#334155; border-radius:4px;
            }
            QSlider::handle:vertical {
                background:#3b82f6; width:16px; height:16px;
                margin:0 -4px; border-radius:8px;
            }
            QSlider::sub-page:vertical {
                background: qlineargradient(x1:0,y1:1,x2:0,y2:0,
                    stop:0 #10b981, stop:0.6 #f59e0b, stop:1 #ef4444);
                border-radius:4px;
            }
        """)
        self._pwr_slider.valueChanged.connect(self._on_power_change)

        self._pwr_bar = _PowerBar()
        self._pwr_bar.setFixedHeight(80)

        self._pwr_lbl = QLabel("0.0 W\n-∞ dBm")
        self._pwr_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._pwr_lbl.setStyleSheet("color:#f59e0b; font-family:Consolas; font-size:11px; border:none; background:transparent;")

        pwr_lay.addStretch()
        pwr_lay.addWidget(self._pwr_slider)
        pwr_lay.addWidget(self._pwr_bar)
        pwr_lay.addWidget(self._pwr_lbl)
        pwr_lay.addStretch()
        root.addWidget(pwr_box)

        # ── 4. BAŞLAT / DURDUR ──────────────────────────────────────────
        self.btn_start = QPushButton("▶  TAARRUZU BAŞLAT")
        self.btn_start.setFixedHeight(48)
        self.btn_start.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.btn_start.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 #065f46, stop:1 #022c22);
                color: #10b981; border: 2px solid #10b981; border-radius: 8px;
            }
            QPushButton:hover { background: #047857; color: #6ee7b7; }
            QPushButton:pressed { background: #022c22; }
            QPushButton:disabled { background: #1e293b; color: #475569; border-color: #334155; }
        """)
        self.btn_start.clicked.connect(self._on_start)
        root.addWidget(self.btn_start)

        self.btn_stop = QPushButton("■  DURDUR")
        self.btn_stop.setFixedHeight(38)
        self.btn_stop.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 #7f1d1d, stop:1 #450a0a);
                color: #ef4444; border: 2px solid #ef4444; border-radius: 8px;
            }
            QPushButton:hover { background: #991b1b; color: #fca5a5; }
            QPushButton:pressed { background: #450a0a; }
            QPushButton:disabled { background: #1e293b; color: #475569; border-color: #334155; }
        """)
        self.btn_stop.clicked.connect(self._on_stop)
        root.addWidget(self.btn_stop)

        # ── 5. Etkinlik Gauge ───────────────────────────────────────────
        self._gauge = _MiniGauge()
        root.addWidget(self._gauge)

        root.addStretch(1)

        # Etkinlik simülasyon zamanlayıcısı
        self._eff_timer = QTimer(self)
        self._eff_timer.timeout.connect(self._update_effectiveness)
        self._eff_timer.start(500)

    # ── Yardımcılar ──────────────────────────────────────────────────────────
    @staticmethod
    def _gbox_style(accent: str) -> str:
        return (
            f"QGroupBox {{ border:1px solid #334155; border-radius:8px; "
            f"margin-top:12px; padding-top:8px; font-weight:bold; "
            f"color:{accent}; font-size:11px; font-family:Consolas; }}"
            f"QGroupBox::title {{ subcontrol-origin:margin; left:8px; padding:0 4px; }}"
        )

    def _refresh_mode_styles(self, active_id: int):
        ACTIVE = (
            "QPushButton { background:#1e3a8a; color:#60a5fa; "
            "border:1px solid #3b82f6; border-radius:6px; font-family:Consolas; "
            "font-size:9pt; font-weight:bold; }"
        )
        IDLE = (
            "QPushButton { background:#0f172a; color:#475569; "
            "border:1px solid #334155; border-radius:6px; font-family:Consolas; "
            "font-size:9pt; font-weight:bold; }"
            "QPushButton:hover { color:#94a3b8; border-color:#475569; }"
        )
        for bid, btn in self._mode_btns.items():
            btn.setStyleSheet(ACTIVE if bid == active_id else IDLE)

    def _on_power_change(self, val: int):
        self._power_w = val / 10.0
        self._pwr_bar.set_level(self._power_w)
        dbm = 10 * math.log10(self._power_w * 1000) if self._power_w > 0 else float("-inf")
        dbm_str = f"{dbm:.1f}" if self._power_w > 0 else "-∞"
        self._pwr_lbl.setText(f"{self._power_w:.1f} W\n{dbm_str} dBm")

    def _on_start(self):
        if self._jam_active:
            return
        self._jam_active = True
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        mode = self._get_mode_label()
        if self.state_manager:
            self.state_manager.update_et_state(True, 2400.0, mode)

    def _on_stop(self):
        if not self._jam_active:
            return
        self._jam_active = False
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self._gauge.set_value(0)
        if self.state_manager:
            self.state_manager.update_et_state(False, 2400.0, "BEKLEMEDE")

    def _get_mode_label(self) -> str:
        bid = self._mode_group.checkedId()
        return ["TEKLİ", "ÇOKLU", "BARAJ"][bid] if bid >= 0 else "TEKLİ"

    def _update_effectiveness(self):
        import random
        if self._jam_active:
            base = min(95, 35 + self._power_w * 10 + random.uniform(-5, 5))
            self._gauge.set_value(base)
        else:
            self._gauge.set_value(0)

    # ── Dışarıdan çağrılan API (main_window.py uyumlu) ───────────────────────
    def update_ai_results(self, mod_type: str, snr: float, confidence: float):
        """main_window.py → simulate_live_data() tarafından çağrılır."""
        self.lbl_modulation.setText(f"Hedef Sinyal: {mod_type}")
        self.lbl_snr.setText(f"Tahmini SNR: {snr} dB")
        self.lbl_confidence.setText(f"Yapay Zeka Güven Skoru: %{confidence:.1f}")
        rec = AI_RECS.get(mod_type, "Bilinmiyor")
        self._ai_rec_lbl.setText(f"AI Öneri: {rec}")

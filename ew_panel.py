"""
Elektronik Harp - Sürekli Karıştırma Kontrol Paneli
Military EW Continuous Jamming GUI  |  PyQt6  |  Dark HMI
"""

import sys
import random
import math
from datetime import datetime
from collections import deque

import numpy as np

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSlider, QTableWidget, QTableWidgetItem,
    QFrame, QTextEdit, QGroupBox, QButtonGroup, QHeaderView,
    QSizePolicy, QGridLayout, QSpacerItem, QAbstractItemView,
)
from PyQt6.QtCore import Qt, QTimer, QRect, QPoint, QSize, QRectF, QPointF
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QFontMetrics,
    QLinearGradient, QPainterPath, QPolygonF, QImage,
    QPixmap, QPalette,
)

# ─── Renk paleti ────────────────────────────────────────────────────────────
C_BG        = QColor("#0d0d1a")
C_BG2       = QColor("#1a1a2e")
C_BG3       = QColor("#16213e")
C_PANEL     = QColor("#0f3460")
C_GREEN     = QColor("#00ff41")
C_GREEN_DIM = QColor("#007a20")
C_RED       = QColor("#ff0040")
C_RED_DIM   = QColor("#7a001f")
C_YELLOW    = QColor("#ffcc00")
C_CYAN      = QColor("#00d4ff")
C_WHITE     = QColor("#e0e0e0")
C_GRAY      = QColor("#4a4a6a")
C_BORDER    = QColor("#2a2a4a")

FONT_MONO = QFont("Consolas", 9)
FONT_MONO_SM = QFont("Consolas", 8)
FONT_TITLE = QFont("Consolas", 10, QFont.Weight.Bold)
FONT_BIG   = QFont("Consolas", 14, QFont.Weight.Bold)
FONT_HUGE  = QFont("Consolas", 11, QFont.Weight.Bold)

# ─── Modülasyon tipleri ve AI önerileri ─────────────────────────────────────
MODULATIONS = ["AM", "FM", "BPSK", "QPSK", "8PSK", "QAM-16", "OFDM", "FSK"]
AI_RECS = {
    "AM":    "Genlik Baskılama",
    "FM":    "Frekans Kayması",
    "BPSK":  "Faz Bozma",
    "QPSK":  "Faz Bozma",
    "8PSK":  "Çok Tonlu Karıştırma",
    "QAM-16":"Gürültü Enjeksiyonu",
    "OFDM":  "Alt Taşıyıcı Baskı",
    "FSK":   "Frekans Atlama Takibi",
}
BANDS = ["VHF", "UHF", "L-Band", "S-Band", "C-Band", "X-Band"]

# ════════════════════════════════════════════════════════════════════════════
#  WaterfallWidget  –  spektrum waterfall (frekans × zaman × güç)
# ════════════════════════════════════════════════════════════════════════════
class WaterfallWidget(QWidget):
    N_FREQ  = 512   # frekans çözünürlüğü
    N_HIST  = 160   # zaman geçmişi (satır)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 300)
        self.history = deque(maxlen=self.N_HIST)
        self._image  = None

        # Sahte frekans aralığı
        self.freq_min = 400.0   # MHz
        self.freq_max = 3000.0

        # Aktif sinyaller (merkez frekans, güç ofseti, bant)
        self.targets: list[dict] = []
        self._jam_active  = False
        self._jam_freq    = 900.0
        self._jam_bw      = 80.0

    def set_jam_state(self, active: bool, freq: float, bw: float):
        self._jam_active = active
        self._jam_freq   = freq
        self._jam_bw     = bw

    def add_target(self, freq_mhz: float, power_db: float):
        self.targets.append({"f": freq_mhz, "p": power_db, "w": 15.0})

    def _generate_row(self) -> np.ndarray:
        freqs  = np.linspace(self.freq_min, self.freq_max, self.N_FREQ)
        noise  = np.random.normal(-80, 2, self.N_FREQ)

        for t in self.targets:
            fc, pw, bw = t["f"], t["p"], t["w"]
            sig = pw * np.exp(-0.5 * ((freqs - fc) / (bw * 0.5)) ** 2)
            noise = np.maximum(noise, sig - 80)

        if self._jam_active:
            jc, jbw = self._jam_freq, self._jam_bw
            jpower = np.where(
                np.abs(freqs - jc) < jbw / 2,
                np.random.normal(-35, 3, self.N_FREQ),
                0,
            )
            noise = np.maximum(noise, jpower)

        return np.clip(noise, -90, 0)

    def update_frame(self):
        row = self._generate_row()
        self.history.appendleft(row)
        self._rebuild_image()
        self.update()

    def _rebuild_image(self):
        if not self.history:
            return
        arr = np.array(self.history)           # (N_HIST, N_FREQ)
        norm = (arr + 90) / 90.0               # 0..1
        norm = np.clip(norm, 0, 1)

        # Renk haritası: siyah → koyu yeşil → parlak yeşil → sarı → kırmızı
        r = np.zeros_like(norm)
        g = np.zeros_like(norm)
        b = np.zeros_like(norm)

        m1 = norm < 0.4
        m2 = (norm >= 0.4) & (norm < 0.7)
        m3 = (norm >= 0.7) & (norm < 0.9)
        m4 = norm >= 0.9

        # siyah → yeşil
        g[m1] = norm[m1] / 0.4 * 180
        # yeşil → sarı-yeşil
        g[m2] = 180 + (norm[m2] - 0.4) / 0.3 * 75
        r[m2] = (norm[m2] - 0.4) / 0.3 * 180
        # sarı-yeşil → turuncu
        g[m3] = 255
        r[m3] = 180 + (norm[m3] - 0.7) / 0.2 * 75
        # turuncu → kırmızı
        r[m4] = 255
        g[m4] = 255 - (norm[m4] - 0.9) / 0.1 * 255

        rgb = np.stack([
            r.astype(np.uint8),
            g.astype(np.uint8),
            b.astype(np.uint8),
        ], axis=2)

        rows, cols, _ = rgb.shape
        self._image = QImage(
            rgb.tobytes(), cols, rows,
            cols * 3, QImage.Format.Format_RGB888,
        )

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), C_BG)

        pad_l, pad_r = 52, 10
        pad_t, pad_b = 10, 38

        draw_w = self.width()  - pad_l - pad_r
        draw_h = self.height() - pad_t - pad_b

        if self._image:
            scaled = self._image.scaled(
                draw_w, draw_h,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            p.drawImage(QPoint(pad_l, pad_t), scaled)

        # Çerçeve
        p.setPen(QPen(C_BORDER, 1))
        p.drawRect(pad_l, pad_t, draw_w, draw_h)

        # ── Frekans ekseni (X) ──────────────────────────────────────────
        p.setFont(FONT_MONO_SM)
        p.setPen(QPen(C_GRAY, 1))
        n_xtick = 8
        for i in range(n_xtick + 1):
            fx = pad_l + int(i * draw_w / n_xtick)
            fmhz = self.freq_min + i * (self.freq_max - self.freq_min) / n_xtick
            # ızgara
            p.setPen(QPen(QColor("#1e1e3a"), 1))
            p.drawLine(fx, pad_t, fx, pad_t + draw_h)
            p.setPen(QPen(C_GRAY, 1))
            p.drawLine(fx, pad_t + draw_h, fx, pad_t + draw_h + 5)
            lbl = f"{fmhz:.0f}"
            fm  = QFontMetrics(FONT_MONO_SM)
            p.drawText(fx - fm.horizontalAdvance(lbl) // 2,
                       pad_t + draw_h + 18, lbl)

        p.setPen(QPen(C_WHITE, 1))
        p.setFont(FONT_MONO_SM)
        p.drawText(pad_l + draw_w // 2 - 20, self.height() - 4, "Frekans (MHz)")

        # ── Güç ekseni (Y) ──────────────────────────────────────────────
        n_ytick = 6
        for i in range(n_ytick + 1):
            fy  = pad_t + int(i * draw_h / n_ytick)
            db  = 0 - i * 90 // n_ytick
            p.setPen(QPen(QColor("#1e1e3a"), 1))
            p.drawLine(pad_l, fy, pad_l + draw_w, fy)
            p.setPen(QPen(C_GRAY, 1))
            p.drawLine(pad_l - 5, fy, pad_l, fy)
            lbl = f"{db}"
            fm  = QFontMetrics(FONT_MONO_SM)
            p.setFont(FONT_MONO_SM)
            p.setPen(QPen(C_GRAY, 1))
            p.drawText(pad_l - fm.horizontalAdvance(lbl) - 6,
                       fy + 4, lbl)

        # dBm etiketi
        p.save()
        p.translate(12, pad_t + draw_h // 2)
        p.rotate(-90)
        p.setPen(QPen(C_WHITE, 1))
        p.drawText(-20, 0, "dBm")
        p.restore()

        # ── Karıştırıcı bant göstergesi ─────────────────────────────────
        if self._jam_active:
            fspan = self.freq_max - self.freq_min
            x_c = pad_l + int((self._jam_freq - self.freq_min) / fspan * draw_w)
            x_bw = int(self._jam_bw / fspan * draw_w)
            jam_rect = QRect(x_c - x_bw // 2, pad_t, x_bw, draw_h)
            p.fillRect(jam_rect, QColor(255, 0, 64, 30))
            p.setPen(QPen(C_RED, 1, Qt.PenStyle.DashLine))
            p.drawRect(jam_rect)
            p.setFont(FONT_MONO_SM)
            p.setPen(QPen(C_RED, 1))
            p.drawText(x_c - 14, pad_t + 14, "JAM")

        p.end()


# ════════════════════════════════════════════════════════════════════════════
#  GaugeWidget  –  Etkinlik skoru göstergesi (yay tabanlı)
# ════════════════════════════════════════════════════════════════════════════
class GaugeWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._value   = 0       # 0..100
        self._target  = 0
        self.setMinimumSize(180, 120)
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._step)
        self._anim_timer.start(30)

    def set_value(self, v: int):
        self._target = max(0, min(100, v))

    def _step(self):
        diff = self._target - self._value
        if abs(diff) > 0.5:
            self._value += diff * 0.12
            self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), C_BG2)

        cx = self.width() // 2
        cy = int(self.height() * 0.72)
        r  = min(self.width(), self.height() * 1.4) // 2 - 12

        start_a = 210  # derece (Qt: saat yönü tersine)
        span_a  = 120  # toplam yay = 120°

        # ── Arka plan yayı ──────────────────────────────────────────────
        arc_rect = QRectF(cx - r, cy - r, 2 * r, 2 * r)
        p.setPen(QPen(C_BORDER, 8, Qt.PenStyle.SolidLine,
                      Qt.PenCapStyle.RoundCap))
        p.drawArc(arc_rect,
                  int(start_a * 16),
                  int(-span_a * 16))   # sola doğru (-120°)

        # ── Değer yayı (renk gradyanı) ──────────────────────────────────
        frac = self._value / 100.0
        if frac > 0:
            # yeşil→sarı→kırmızı
            if frac < 0.5:
                t = frac / 0.5
                rc = int(255 * t); gc = 255; bc = 0
            else:
                t = (frac - 0.5) / 0.5
                rc = 255; gc = int(255 * (1 - t)); bc = 0
            val_color = QColor(rc, gc, bc)
            p.setPen(QPen(val_color, 8, Qt.PenStyle.SolidLine,
                          Qt.PenCapStyle.RoundCap))
            p.drawArc(arc_rect,
                      int(start_a * 16),
                      int(-span_a * frac * 16))

        # ── İbre ────────────────────────────────────────────────────────
        angle_deg = start_a - span_a * frac   # derece
        angle_rad = math.radians(angle_deg)
        needle_len = r - 6
        nx = cx + needle_len * math.cos(angle_rad)
        ny = cy - needle_len * math.sin(angle_rad)
        p.setPen(QPen(C_WHITE, 2, Qt.PenStyle.SolidLine,
                      Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(cx, cy), QPointF(nx, ny))
        p.setBrush(QBrush(C_GRAY))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(cx, cy), 5, 5)

        # ── Ölçek etiketleri ────────────────────────────────────────────
        p.setFont(FONT_MONO_SM)
        for val in [0, 25, 50, 75, 100]:
            a  = math.radians(start_a - span_a * val / 100)
            tx = cx + (r + 14) * math.cos(a)
            ty = cy - (r + 14) * math.sin(a)
            p.setPen(QPen(C_GRAY, 1))
            fm = QFontMetrics(FONT_MONO_SM)
            lbl = str(val)
            p.drawText(int(tx) - fm.horizontalAdvance(lbl) // 2,
                       int(ty) + 4, lbl)

        # ── Sayısal değer ───────────────────────────────────────────────
        p.setFont(FONT_BIG)
        pct_str = f"{int(self._value):3d}%"
        fm = QFontMetrics(FONT_BIG)
        p.setPen(QPen(C_GREEN if self._value >= 50 else C_YELLOW, 1))
        p.drawText(cx - fm.horizontalAdvance(pct_str) // 2, cy + 22, pct_str)

        # ── Başlık ──────────────────────────────────────────────────────
        p.setFont(FONT_MONO_SM)
        p.setPen(QPen(C_GRAY, 1))
        lbl2 = "ETKİNLİK SKORU"
        fm2  = QFontMetrics(FONT_MONO_SM)
        p.drawText(cx - fm2.horizontalAdvance(lbl2) // 2, 14, lbl2)

        p.end()


# ════════════════════════════════════════════════════════════════════════════
#  PowerBarWidget  –  dikey güç göstergesi
# ════════════════════════════════════════════════════════════════════════════
class PowerBarWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._level = 0.0   # 0..5 W
        self.setMinimumWidth(28)
        self.setMaximumWidth(36)

    def set_level(self, w: float):
        self._level = w
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), C_BG2)

        pad = 6
        bar_h = self.height() - 2 * pad
        bar_w = self.width()  - 2 * pad
        frac  = self._level / 5.0

        # arka plan
        p.fillRect(pad, pad, bar_w, bar_h, C_BORDER)

        # dolgu gradyan
        fill_h = int(bar_h * frac)
        if fill_h > 0:
            grad = QLinearGradient(0, pad + bar_h, 0, pad + bar_h - fill_h)
            grad.setColorAt(0.0, QColor("#00ff41"))
            grad.setColorAt(0.6, QColor("#ffcc00"))
            grad.setColorAt(1.0, QColor("#ff0040"))
            p.fillRect(pad, pad + bar_h - fill_h, bar_w, fill_h,
                       QBrush(grad))
        p.end()


# ════════════════════════════════════════════════════════════════════════════
#  Yardımcı bileşenler
# ════════════════════════════════════════════════════════════════════════════
def make_separator(orientation="h") -> QFrame:
    line = QFrame()
    if orientation == "h":
        line.setFrameShape(QFrame.Shape.HLine)
    else:
        line.setFrameShape(QFrame.Shape.VLine)
    line.setStyleSheet(f"color: {C_BORDER.name()}; background: {C_BORDER.name()};")
    return line


def make_label(text: str, font=None, color=C_WHITE, align=Qt.AlignmentFlag.AlignLeft) -> QLabel:
    lbl = QLabel(text)
    lbl.setFont(font or FONT_MONO)
    lbl.setAlignment(align)
    lbl.setStyleSheet(f"color: {color.name()}; background: transparent;")
    return lbl


def panel_style(radius: int = 6) -> str:
    return (
        f"background-color: {C_BG2.name()}; "
        f"border: 1px solid {C_BORDER.name()}; "
        f"border-radius: {radius}px;"
    )


# ════════════════════════════════════════════════════════════════════════════
#  Üst Durum Çubuğu
# ════════════════════════════════════════════════════════════════════════════
class StatusBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(56)
        self.setStyleSheet(f"background: {C_BG3.name()}; border-bottom: 2px solid {C_GREEN_DIM.name()};")

        root = QHBoxLayout(self)
        root.setContentsMargins(16, 6, 16, 6)
        root.setSpacing(32)

        # Sol: logo / sistem adı
        logo = make_label("◈ EH-KONTROL SİSTEMİ", FONT_BIG, C_GREEN)
        root.addWidget(logo)
        root.addStretch(1)

        self._status_dot = make_label("●", FONT_BIG, C_RED)
        self._status_lbl = make_label("PASSIVE", FONT_TITLE, C_RED)
        root.addWidget(self._status_dot)
        root.addWidget(self._status_lbl)
        root.addSpacing(24)

        root.addWidget(make_label("FREKANS:", FONT_MONO, C_GRAY))
        self._freq_lbl = make_label("---.- MHz", FONT_TITLE, C_CYAN)
        root.addWidget(self._freq_lbl)
        root.addSpacing(24)

        root.addWidget(make_label("MOD:", FONT_MONO, C_GRAY))
        self._mode_lbl = make_label("---", FONT_TITLE, C_WHITE)
        root.addWidget(self._mode_lbl)
        root.addSpacing(24)

        root.addWidget(make_label("GÜÇ:", FONT_MONO, C_GRAY))
        self._power_lbl = make_label("0.0 W / 0.0 dBm", FONT_TITLE, C_YELLOW)
        root.addWidget(self._power_lbl)

        # Saat
        root.addSpacing(32)
        self._time_lbl = make_label("00:00:00", FONT_MONO, C_GRAY)
        root.addWidget(self._time_lbl)

        self._tick = QTimer(self)
        self._tick.timeout.connect(self._update_clock)
        self._tick.start(1000)
        self._update_clock()

    def _update_clock(self):
        self._time_lbl.setText(datetime.now().strftime("%H:%M:%S"))

    def set_active(self, active: bool):
        if active:
            self._status_dot.setStyleSheet("color: #00ff41; background: transparent;")
            self._status_lbl.setStyleSheet("color: #00ff41; background: transparent;")
            self._status_lbl.setText("AKTİF")
        else:
            self._status_dot.setStyleSheet("color: #ff0040; background: transparent;")
            self._status_lbl.setStyleSheet("color: #ff0040; background: transparent;")
            self._status_lbl.setText("PASİF")

    def set_freq(self, mhz: float):
        self._freq_lbl.setText(f"{mhz:.1f} MHz")

    def set_mode(self, mode: str):
        self._mode_lbl.setText(mode)

    def set_power(self, watts: float):
        dbm = 10 * math.log10(watts * 1000) if watts > 0 else -999
        dbm_str = f"{dbm:.1f}" if watts > 0 else "-∞"
        self._power_lbl.setText(f"{watts:.1f} W / {dbm_str} dBm")


# ════════════════════════════════════════════════════════════════════════════
#  Sol Panel – Tespit Edilen Hedefler
# ════════════════════════════════════════════════════════════════════════════
class TargetsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(310)
        self.setMaximumWidth(360)

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        hdr = make_label("  ⚡ TESPİT EDİLEN HEDEFLER", FONT_TITLE, C_GREEN)
        hdr.setFixedHeight(28)
        hdr.setStyleSheet(
            f"color: {C_GREEN.name()}; background: {C_BG3.name()}; "
            f"border: 1px solid {C_GREEN_DIM.name()}; border-radius: 4px;"
        )
        root.addWidget(hdr)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Frekans\n(MHz)", "Mod.", "SNR\n(dB)", "Band", "AI\nGüven %"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setStyleSheet("""
            QTableWidget {
                background: #0d0d1a;
                color: #e0e0e0;
                gridline-color: #2a2a4a;
                border: 1px solid #2a2a4a;
                font-family: Consolas;
                font-size: 9pt;
            }
            QTableWidget::item:selected {
                background: #0f3460;
                color: #00ff41;
            }
            QHeaderView::section {
                background: #16213e;
                color: #00d4ff;
                border: 1px solid #2a2a4a;
                font-family: Consolas;
                font-size: 8pt;
                padding: 3px;
            }
        """)
        root.addWidget(self.table)

        # Alt bilgi kutusu
        self._info_box = QLabel("Hedef seçilmedi")
        self._info_box.setWordWrap(True)
        self._info_box.setStyleSheet(
            f"color: {C_GRAY.name()}; background: {C_BG3.name()}; "
            f"border: 1px solid {C_BORDER.name()}; border-radius: 4px; "
            f"padding: 6px; font-family: Consolas; font-size: 8pt;"
        )
        self._info_box.setFixedHeight(54)
        root.addWidget(self._info_box)

    def update_targets(self, targets: list[dict]):
        self.table.setRowCount(0)
        for t in targets:
            row = self.table.rowCount()
            self.table.insertRow(row)

            conf = t["confidence"]
            freq_item  = QTableWidgetItem(f"{t['freq']:.1f}")
            mod_item   = QTableWidgetItem(t["mod"])
            snr_item   = QTableWidgetItem(f"{t['snr']:.1f}")
            band_item  = QTableWidgetItem(t["band"])
            conf_item  = QTableWidgetItem(f"{conf:.0f}%")

            # Renk kodlaması
            if conf >= 85:
                color = C_RED
            elif conf >= 65:
                color = C_YELLOW
            else:
                color = C_WHITE

            for item in [freq_item, mod_item, snr_item, band_item, conf_item]:
                item.setForeground(QBrush(color))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, [freq_item, mod_item, snr_item, band_item, conf_item].index(item), item)

            self.table.setItem(row, 0, freq_item)
            self.table.setItem(row, 1, mod_item)
            self.table.setItem(row, 2, snr_item)
            self.table.setItem(row, 3, band_item)
            self.table.setItem(row, 4, conf_item)
            self.table.setRowHeight(row, 22)

    def set_info(self, text: str):
        self._info_box.setText(text)


# ════════════════════════════════════════════════════════════════════════════
#  Sağ Panel – Karıştırma Kontrolleri
# ════════════════════════════════════════════════════════════════════════════
class JammingControlPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(260)
        self.setMaximumWidth(310)
        self._jam_active = False
        self._power_watts = 0.0

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        # ── Başlık ──────────────────────────────────────────────────────
        hdr = make_label("  ⚙ KARIŞTIRMA KONTROLÜ", FONT_TITLE, C_GREEN)
        hdr.setFixedHeight(28)
        hdr.setStyleSheet(
            f"color: {C_GREEN.name()}; background: {C_BG3.name()}; "
            f"border: 1px solid {C_GREEN_DIM.name()}; border-radius: 4px;"
        )
        root.addWidget(hdr)

        # ── Mod seçici ──────────────────────────────────────────────────
        mode_box = QGroupBox("KARIŞTIRMA MODU")
        mode_box.setStyleSheet("""
            QGroupBox {
                color: #00d4ff; font-family: Consolas; font-size: 9pt;
                border: 1px solid #2a2a4a; border-radius: 4px;
                margin-top: 10px; padding-top: 6px;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 8px; }
        """)
        mode_layout = QHBoxLayout(mode_box)
        mode_layout.setSpacing(4)

        self._mode_group = QButtonGroup(self)
        btn_style = lambda active: (
            f"QPushButton {{ "
            f"background: {'#0f3460' if active else '#0d0d1a'}; "
            f"color: {'#00ff41' if active else '#4a4a6a'}; "
            f"border: 1px solid {'#00ff41' if active else '#2a2a4a'}; "
            f"border-radius: 4px; font-family: Consolas; font-size: 9pt; "
            f"font-weight: bold; padding: 6px 4px; }}"
            f"QPushButton:hover {{ background: #16213e; color: #00d4ff; "
            f"border-color: #00d4ff; }}"
        )

        self._mode_buttons = {}
        for i, lbl in enumerate(["TEKLİ", "ÇOKLU", "BARAJ"]):
            btn = QPushButton(lbl)
            btn.setCheckable(True)
            btn.setStyleSheet(btn_style(i == 0))
            self._mode_group.addButton(btn, i)
            mode_layout.addWidget(btn)
            self._mode_buttons[lbl] = btn

        self._mode_buttons["TEKLİ"].setChecked(True)
        self._mode_group.idToggled.connect(self._on_mode_change)
        root.addWidget(mode_box)

        # ── Modülasyon & AI öneri ────────────────────────────────────────
        mod_frame = QFrame()
        mod_frame.setStyleSheet(panel_style())
        mod_layout = QVBoxLayout(mod_frame)
        mod_layout.setContentsMargins(10, 8, 10, 8)
        mod_layout.setSpacing(4)

        mod_layout.addWidget(make_label("TESPİT MODÜLASYonu", FONT_MONO_SM, C_GRAY))
        self._mod_lbl = make_label("---", FONT_BIG, C_CYAN, Qt.AlignmentFlag.AlignCenter)
        mod_layout.addWidget(self._mod_lbl)

        ai_sep = make_separator()
        mod_layout.addWidget(ai_sep)

        self._ai_lbl = make_label("AI Öneri: ---", FONT_MONO, C_GREEN, Qt.AlignmentFlag.AlignCenter)
        self._ai_lbl.setStyleSheet(
            f"color: {C_GREEN.name()}; background: transparent; "
            f"border: 1px solid {C_GREEN_DIM.name()}; border-radius: 3px; padding: 2px;"
        )
        mod_layout.addWidget(self._ai_lbl)
        root.addWidget(mod_frame)

        # ── Güç kaydırıcısı ─────────────────────────────────────────────
        pwr_box = QGroupBox("GÜÇ AYARI (0 – 5 W)")
        pwr_box.setStyleSheet("""
            QGroupBox {
                color: #00d4ff; font-family: Consolas; font-size: 9pt;
                border: 1px solid #2a2a4a; border-radius: 4px;
                margin-top: 10px; padding-top: 6px;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 8px; }
        """)
        pwr_layout = QHBoxLayout(pwr_box)
        pwr_layout.setSpacing(8)

        self.power_slider = QSlider(Qt.Orientation.Vertical)
        self.power_slider.setRange(0, 50)   # 0.0..5.0 W (×10)
        self.power_slider.setValue(0)
        self.power_slider.setFixedHeight(90)
        self.power_slider.setStyleSheet("""
            QSlider::groove:vertical {
                width: 8px; background: #0d0d1a;
                border: 1px solid #2a2a4a; border-radius: 4px;
            }
            QSlider::handle:vertical {
                background: #00ff41; border: 2px solid #007a20;
                height: 16px; width: 16px;
                margin: 0 -4px; border-radius: 8px;
            }
            QSlider::sub-page:vertical {
                background: qlineargradient(x1:0,y1:1,x2:0,y2:0,
                    stop:0 #00ff41, stop:0.6 #ffcc00, stop:1 #ff0040);
                border-radius: 4px;
            }
        """)
        self.power_slider.valueChanged.connect(self._on_power_change)

        self._pwr_bar = PowerBarWidget()
        self._pwr_val_lbl = make_label("0.0 W\n0.0 dBm", FONT_MONO, C_YELLOW, Qt.AlignmentFlag.AlignCenter)

        pwr_layout.addStretch()
        pwr_layout.addWidget(self.power_slider)
        pwr_layout.addWidget(self._pwr_bar)
        pwr_layout.addWidget(self._pwr_val_lbl)
        pwr_layout.addStretch()
        root.addWidget(pwr_box)

        # ── Büyük operatör butonları ─────────────────────────────────────
        self.btn_start = QPushButton("▶  KARIŞTIRMAYI BAŞLAT")
        self.btn_start.setFixedHeight(52)
        self.btn_start.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        self.btn_start.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 #004d14, stop:1 #002a0a);
                color: #00ff41;
                border: 2px solid #00ff41;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 #006620, stop:1 #003d10);
                border-color: #44ff77;
            }
            QPushButton:pressed {
                background: #001a06;
            }
        """)
        root.addWidget(self.btn_start)

        self.btn_stop = QPushButton("■  DURDUR")
        self.btn_stop.setFixedHeight(44)
        self.btn_stop.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        self.btn_stop.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 #4d0014, stop:1 #2a000a);
                color: #ff0040;
                border: 2px solid #ff0040;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 #660020, stop:1 #3d0010);
                border-color: #ff4477;
            }
            QPushButton:pressed { background: #1a0006; }
        """)
        root.addWidget(self.btn_stop)

        # ── Gauge ────────────────────────────────────────────────────────
        self.gauge = GaugeWidget()
        root.addWidget(self.gauge)

        root.addStretch(1)

    def _on_mode_change(self, btn_id: int, checked: bool):
        if not checked:
            return
        labels = ["TEKLİ", "ÇOKLU", "BARAJ"]
        for lbl, btn in self._mode_buttons.items():
            if lbl == labels[btn_id]:
                btn.setStyleSheet(
                    "QPushButton { background: #0f3460; color: #00ff41; "
                    "border: 1px solid #00ff41; border-radius: 4px; "
                    "font-family: Consolas; font-size: 9pt; font-weight: bold; padding: 6px 4px; }"
                    "QPushButton:hover { background: #16213e; color: #00d4ff; border-color: #00d4ff; }"
                )
            else:
                btn.setStyleSheet(
                    "QPushButton { background: #0d0d1a; color: #4a4a6a; "
                    "border: 1px solid #2a2a4a; border-radius: 4px; "
                    "font-family: Consolas; font-size: 9pt; font-weight: bold; padding: 6px 4px; }"
                    "QPushButton:hover { background: #16213e; color: #00d4ff; border-color: #00d4ff; }"
                )

    def _on_power_change(self, val: int):
        self._power_watts = val / 10.0
        self._pwr_bar.set_level(self._power_watts)
        dbm = 10 * math.log10(self._power_watts * 1000) if self._power_watts > 0 else float('-inf')
        dbm_str = f"{dbm:.1f}" if self._power_watts > 0 else "-∞"
        self._pwr_val_lbl.setText(f"{self._power_watts:.1f} W\n{dbm_str} dBm")

    def set_modulation(self, mod: str):
        self._mod_lbl.setText(mod)
        rec = AI_RECS.get(mod, "---")
        self._ai_lbl.setText(f"AI Öneri: {rec}")

    def get_mode(self) -> str:
        bid = self._mode_group.checkedId()
        return ["TEKLİ", "ÇOKLU", "BARAJ"][bid] if bid >= 0 else "TEKLİ"

    def get_power(self) -> float:
        return self._power_watts


# ════════════════════════════════════════════════════════════════════════════
#  Alt Log Bölmesi
# ════════════════════════════════════════════════════════════════════════════
class LogPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(120)

        root = QHBoxLayout(self)
        root.setContentsMargins(8, 4, 8, 4)
        root.setSpacing(8)

        hdr = make_label("  ▸ SİSTEM KAYITLARI", FONT_TITLE, C_CYAN)
        hdr.setFixedWidth(170)
        root.addWidget(hdr)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setFont(QFont("Consolas", 8))
        self.log.setStyleSheet("""
            QTextEdit {
                background: #0a0a14;
                color: #00d4ff;
                border: 1px solid #2a2a4a;
                border-radius: 4px;
            }
        """)
        root.addWidget(self.log)

    def append(self, level: str, msg: str):
        ts  = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        colors = {"INFO": "#00d4ff", "WARN": "#ffcc00", "ALERT": "#ff0040", "OK": "#00ff41"}
        col = colors.get(level, "#e0e0e0")
        html = (
            f'<span style="color:#4a4a6a;">[{ts}]</span> '
            f'<span style="color:{col}; font-weight:bold;">[{level}]</span> '
            f'<span style="color:#c0c0c0;">{msg}</span>'
        )
        self.log.append(html)
        sb = self.log.verticalScrollBar()
        sb.setValue(sb.maximum())


# ════════════════════════════════════════════════════════════════════════════
#  Ana Pencere
# ════════════════════════════════════════════════════════════════════════════
class EWMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EH Kontrol Sistemi — Sürekli Karıştırma")
        self.setMinimumSize(1280, 780)
        self._jam_active = False
        self._targets: list[dict] = []
        self._active_mod = "BPSK"
        self._frame_count = 0

        self._build_ui()
        self._connect_signals()
        self._seed_targets()

        # Gerçek zamanlı güncelleme zamanlayıcısı
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(80)   # ~12 fps

    # ── UI İnşası ──────────────────────────────────────────────────────
    def _build_ui(self):
        root_w = QWidget()
        root_w.setStyleSheet(f"background: {C_BG.name()};")
        self.setCentralWidget(root_w)

        root_layout = QVBoxLayout(root_w)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Durum çubuğu
        self.status_bar = StatusBar()
        root_layout.addWidget(self.status_bar)

        # Orta gövde
        body = QHBoxLayout()
        body.setContentsMargins(6, 6, 6, 4)
        body.setSpacing(6)

        # Sol panel
        self.targets_panel = TargetsPanel()
        body.addWidget(self.targets_panel)

        body.addWidget(make_separator("v"))

        # Merkez: waterfall
        center = QVBoxLayout()
        center.setSpacing(4)
        center_hdr = make_label("  ◈ SPEKTRUM WATERFALL DİSPLAYI", FONT_TITLE, C_CYAN)
        center_hdr.setFixedHeight(28)
        center_hdr.setStyleSheet(
            f"color: {C_CYAN.name()}; background: {C_BG3.name()}; "
            f"border: 1px solid {C_BORDER.name()}; border-radius: 4px;"
        )
        center.addWidget(center_hdr)
        self.waterfall = WaterfallWidget()
        center.addWidget(self.waterfall)
        body.addLayout(center, stretch=1)

        body.addWidget(make_separator("v"))

        # Sağ panel
        self.jam_ctrl = JammingControlPanel()
        body.addWidget(self.jam_ctrl)

        root_layout.addLayout(body, stretch=1)

        # Alt log
        root_layout.addWidget(make_separator())
        self.log_panel = LogPanel()
        root_layout.addWidget(self.log_panel)

    def _connect_signals(self):
        self.jam_ctrl.btn_start.clicked.connect(self._on_start)
        self.jam_ctrl.btn_stop.clicked.connect(self._on_stop)

    # ── Hedef Başlangıç Verisi ──────────────────────────────────────────
    def _seed_targets(self):
        self._targets = [
            {"freq": 433.9,  "mod": "AM",    "snr": 18.2, "band": "UHF",    "confidence": 92.1},
            {"freq": 869.5,  "mod": "FSK",   "snr": 12.7, "band": "UHF",    "confidence": 78.4},
            {"freq": 1227.6, "mod": "BPSK",  "snr": 21.3, "band": "L-Band", "confidence": 95.6},
            {"freq": 2404.0, "mod": "OFDM",  "snr": 9.1,  "band": "S-Band", "confidence": 64.8},
            {"freq": 915.0,  "mod": "QAM-16","snr": 15.5, "band": "UHF",    "confidence": 87.2},
        ]
        for t in self._targets:
            self.waterfall.add_target(t["freq"], -30 + random.uniform(-10, 5))

        self.targets_panel.update_targets(self._targets)
        self._active_mod = self._targets[0]["mod"]
        self.jam_ctrl.set_modulation(self._active_mod)
        self.log_panel.append("INFO", "Hedef veritabanı yüklendi — 5 sinyal tespit edildi.")

    # ── Zamanlayıcı Döngüsü ─────────────────────────────────────────────
    def _tick(self):
        self._frame_count += 1
        self.waterfall.update_frame()

        # Hedefleri yavaşça güncelle (her 15 karede bir)
        if self._frame_count % 15 == 0:
            for t in self._targets:
                t["snr"]        += random.uniform(-0.8, 0.8)
                t["confidence"] += random.uniform(-1.5, 1.5)
                t["confidence"]  = max(20, min(99, t["confidence"]))
                t["freq"]       += random.uniform(-0.1, 0.1)
            self.targets_panel.update_targets(self._targets)

        # Güç dalgalanması (karıştırma aktifse)
        if self._jam_active and self._frame_count % 6 == 0:
            score_base = min(95, 40 + self.jam_ctrl.get_power() * 11 +
                             random.uniform(-6, 6))
            self.jam_ctrl.gauge.set_value(int(score_base))

        # Durum çubuğu
        freq = self._targets[0]["freq"] if self._targets else 0
        self.status_bar.set_freq(freq)
        self.status_bar.set_power(self.jam_ctrl.get_power())
        self.status_bar.set_mode(self.jam_ctrl.get_mode())

    # ── Buton Aksiyonları ───────────────────────────────────────────────
    def _on_start(self):
        if self._jam_active:
            return
        self._jam_active = True
        pwr  = self.jam_ctrl.get_power()
        mode = self.jam_ctrl.get_mode()
        freq = self._targets[0]["freq"] if self._targets else 900.0
        bw   = {"TEKLİ": 50, "ÇOKLU": 150, "BARAJ": 600}[mode]

        self.waterfall.set_jam_state(True, freq, bw)
        self.status_bar.set_active(True)
        self.jam_ctrl.gauge.set_value(0)

        self.log_panel.append("OK",    f"Karıştırma BAŞLATILDI → Mod:{mode}  Güç:{pwr:.1f}W  Frekans:{freq:.1f}MHz")
        self.log_panel.append("INFO",  f"AI Öneri uygulandı: {AI_RECS.get(self._active_mod, '---')}")
        self.log_panel.append("ALERT", f"Hedef sinyaller bastırılıyor...")

        self.jam_ctrl.btn_start.setEnabled(False)
        self.jam_ctrl.btn_stop.setEnabled(True)

    def _on_stop(self):
        if not self._jam_active:
            return
        self._jam_active = False
        self.waterfall.set_jam_state(False, 0, 0)
        self.status_bar.set_active(False)
        self.jam_ctrl.gauge.set_value(0)
        self.log_panel.append("WARN", "Karıştırma DURDURULDU — sistem pasif moda alındı.")

        self.jam_ctrl.btn_start.setEnabled(True)
        self.jam_ctrl.btn_stop.setEnabled(False)


# ════════════════════════════════════════════════════════════════════════════
#  Uygulama Başlatma
# ════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("EH Kontrol Sistemi")

    # Koyu global tema
    pal = app.palette()
    pal.setColor(QPalette.ColorRole.Window,          C_BG)
    pal.setColor(QPalette.ColorRole.WindowText,      C_WHITE)
    pal.setColor(QPalette.ColorRole.Base,            C_BG2)
    pal.setColor(QPalette.ColorRole.AlternateBase,   C_BG3)
    pal.setColor(QPalette.ColorRole.Text,            C_WHITE)
    pal.setColor(QPalette.ColorRole.Button,          C_BG3)
    pal.setColor(QPalette.ColorRole.ButtonText,      C_WHITE)
    pal.setColor(QPalette.ColorRole.Highlight,       C_PANEL)
    pal.setColor(QPalette.ColorRole.HighlightedText, C_GREEN)
    app.setPalette(pal)

    win = EWMainWindow()
    win.show()
    sys.exit(app.exec())

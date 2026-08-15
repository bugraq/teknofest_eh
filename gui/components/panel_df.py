"""
Yön Bulma (Direction Finding / AoA) Paneli
==========================================
Tespit edilen sinyalin geliş açısını (Bearing / Angle of Arrival) gösteren
radar tipi pusula widget'ı.

Şartname madde 12 (Yön Bulma, RMS 3-5°) ile uyumludur. Gerçek AoA donanımı
(4'lü patch anten) henüz bağlı olmadığı için açı GERÇEKÇİ biçimde simüle edilir:
  - "gerçek" açı yavaş rastgele yürüyüşle gezer (stabil değil — sahada olduğu gibi)
  - gösterilen açı = gerçek açı + Gauss gürültü (RMS ~4°)
main_window bu paneli update_bearing() ile besler; sinyal yokken tarama modundadır.
"""

import math
from collections import deque
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGroupBox
from PyQt6.QtCore import Qt, QTimer, QPointF
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QFont, QFontMetrics


class _CompassWidget(QWidget):
    """Kuzey üstte (0°), saat yönünde artan açı gösteren radar pusulası."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(230)

        self._target_bearing = 0.0    # main_window'un beslediği hedef açı
        self._draw_bearing   = 0.0    # ekranda yumuşak hareket için ara değer
        self._rms            = 4.0    # belirsizlik konisi yarı-açısı (derece)
        self._scanning       = True   # sinyal yokken dönen tarama çizgisi
        self._sweep_angle    = 0.0
        self._history: deque = deque(maxlen=40)  # son açı izleri (soluk noktalar)

        # Yumuşak animasyon + tarama için iç zamanlayıcı
        self._anim = QTimer(self)
        self._anim.timeout.connect(self._step)
        self._anim.start(33)

    # ── Dışarıdan çağrılan API ───────────────────────────────────────────────
    def set_scanning(self, scanning: bool):
        self._scanning = scanning

    def update_bearing(self, bearing_deg: float, rms_deg: float = 4.0):
        self._target_bearing = bearing_deg % 360.0
        self._rms = rms_deg
        self._history.append(self._target_bearing)

    # ── İç animasyon ─────────────────────────────────────────────────────────
    def _step(self):
        # İbreyi hedefe en kısa yaydan yumuşakça yaklaştır
        diff = (self._target_bearing - self._draw_bearing + 540) % 360 - 180
        self._draw_bearing = (self._draw_bearing + diff * 0.22) % 360
        if self._scanning:
            self._sweep_angle = (self._sweep_angle + 4.0) % 360
        self.update()

    # ── Çizim ─────────────────────────────────────────────────────────────────
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(self.rect(), QColor("#0a0f1e"))

        cx, cy = w // 2, h // 2
        r = min(w, h) // 2 - 18

        # Konsantrik halkalar
        p.setPen(QPen(QColor("#1e293b"), 1))
        for rr in (r, int(r * 0.66), int(r * 0.33)):
            p.drawEllipse(QPointF(cx, cy), rr, rr)

        # Çapraz eksenler
        p.setPen(QPen(QColor("#1e293b"), 1, Qt.PenStyle.DashLine))
        p.drawLine(cx - r, cy, cx + r, cy)
        p.drawLine(cx, cy - r, cx, cy + r)

        # Derece işaretleri + N/E/S/W
        p.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
        for deg in range(0, 360, 30):
            rad = math.radians(deg - 90)
            x1 = cx + (r - 6) * math.cos(rad)
            y1 = cy + (r - 6) * math.sin(rad)
            x2 = cx + r * math.cos(rad)
            y2 = cy + r * math.sin(rad)
            p.setPen(QPen(QColor("#334155"), 1))
            p.drawLine(QPointF(x1, y1), QPointF(x2, y2))
        labels = {0: "K", 90: "D", 180: "G", 270: "B"}   # Kuzey/Doğu/Güney/Batı
        p.setPen(QPen(QColor("#64748b")))
        fm = QFontMetrics(QFont("Consolas", 8, QFont.Weight.Bold))
        p.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        for deg, txt in labels.items():
            rad = math.radians(deg - 90)
            lx = cx + (r - 16) * math.cos(rad) - fm.horizontalAdvance(txt) / 2
            ly = cy + (r - 16) * math.sin(rad) + 4
            p.drawText(int(lx), int(ly), txt)

        # Tarama çizgisi (sinyal yokken)
        if self._scanning:
            rad = math.radians(self._sweep_angle - 90)
            grad_col = QColor("#10b981")
            grad_col.setAlpha(120)
            p.setPen(QPen(grad_col, 2))
            p.drawLine(QPointF(cx, cy),
                       QPointF(cx + r * math.cos(rad), cy + r * math.sin(rad)))
        else:
            # Geçmiş açı izleri (soluk yeşil noktalar)
            for i, b in enumerate(self._history):
                a = int(30 + 120 * i / max(1, len(self._history)))
                col = QColor("#10b981"); col.setAlpha(a)
                rad = math.radians(b - 90)
                hx = cx + (r - 3) * math.cos(rad)
                hy = cy + (r - 3) * math.sin(rad)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(col))
                p.drawEllipse(QPointF(hx, hy), 2, 2)

            # Belirsizlik konisi (±RMS)
            rad = math.radians(self._draw_bearing - 90)
            span = math.radians(max(2.0, self._rms))
            cone = QColor("#ef4444"); cone.setAlpha(45)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(cone))
            path_pts = [QPointF(cx, cy)]
            for k in range(-3, 4):
                a = rad + span * k / 3.0
                path_pts.append(QPointF(cx + r * math.cos(a), cy + r * math.sin(a)))
            p.drawPolygon(*path_pts)

            # İbre (bearing)
            p.setPen(QPen(QColor("#ef4444"), 2.5))
            p.drawLine(QPointF(cx, cy),
                       QPointF(cx + (r - 4) * math.cos(rad), cy + (r - 4) * math.sin(rad)))
            # Uç oku
            p.setBrush(QBrush(QColor("#ef4444")))
            p.setPen(Qt.PenStyle.NoPen)
            tx = cx + (r - 4) * math.cos(rad)
            ty = cy + (r - 4) * math.sin(rad)
            p.drawEllipse(QPointF(tx, ty), 4, 4)

        # Merkez nokta
        p.setBrush(QBrush(QColor("#94a3b8")))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(cx, cy), 3, 3)

        # Merkez üstü açı değeri
        p.setFont(QFont("Consolas", 13, QFont.Weight.Bold))
        if self._scanning:
            p.setPen(QPen(QColor("#10b981")))
            txt = "TARANIYOR"
            p.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        else:
            p.setPen(QPen(QColor("#ef4444")))
            txt = f"{self._draw_bearing:05.1f}°"
        fm2 = QFontMetrics(p.font())
        p.drawText(cx - fm2.horizontalAdvance(txt) // 2, cy + r + 12, txt)
        p.end()


class DirectionFinderPanel(QWidget):
    """Ana ekranda kullanılan Yön Bulma paneli (pusula + bilgi satırları)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        box = QGroupBox("YÖN BULMA (DF / AoA)")
        box.setStyleSheet(
            "QGroupBox { border:1px solid #334155; border-radius:8px; "
            "margin-top:12px; padding-top:8px; font-weight:bold; "
            "color:#10b981; font-size:11px; font-family:Consolas; }"
            "QGroupBox::title { subcontrol-origin:margin; left:8px; padding:0 4px; }"
        )
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        inner = QVBoxLayout(box)
        inner.setContentsMargins(8, 16, 8, 8)
        inner.setSpacing(4)

        self._compass = _CompassWidget()
        inner.addWidget(self._compass)

        self._info_lbl = QLabel("Kaynak: ---   |   SNR: -- dB")
        self._info_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._info_lbl.setStyleSheet(
            "color:#94a3b8; font-size:11px; font-family:Consolas; "
            "border:none; background:transparent;"
        )
        inner.addWidget(self._info_lbl)

        self._rms_lbl = QLabel("RMS Doğruluk: ±4.0°")
        self._rms_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._rms_lbl.setStyleSheet(
            "color:#64748b; font-size:10px; font-family:Consolas; "
            "border:none; background:transparent;"
        )
        inner.addWidget(self._rms_lbl)

        # Veri kaynağı rozeti: gösterilen açı gerçek anten ölçümü mü, yer tutucu mu.
        # Ekranda açıkça yazmazsa simülasyon ölçüm sanılır — hakem önünde de,
        # kendi ekibimiz içinde de yanlış anlaşılmaya açık.
        self._src_lbl = QLabel("● VERİ YOK")
        self._src_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inner.addWidget(self._src_lbl)
        self._set_source("none")

        outer.addWidget(box)

    def _set_source(self, kind: str):
        """kind: 'real' (anten ölçümü) | 'sim' (yer tutucu) | 'none' (veri yok)"""
        styles = {
            "real": ("● ANTEN ÖLÇÜMÜ", "#10b981", "#052e1a", "#065f46"),
            "sim":  ("▲ SİMÜLASYON — ÖLÇÜM DEĞİL", "#f59e0b", "#1c1917", "#78350f"),
            "none": ("● VERİ YOK", "#475569", "#0a0f1e", "#1e293b"),
        }
        text, fg, bg, border = styles.get(kind, styles["none"])
        self._src_lbl.setText(text)
        self._src_lbl.setStyleSheet(
            f"color:{fg}; background:{bg}; border:1px solid {border}; "
            f"border-radius:3px; padding:2px; "
            f"font-family:Consolas; font-size:9px; font-weight:bold;"
        )

    # ── Dışarıdan çağrılan API (main_window uyumlu) ──────────────────────────
    def update_bearing(self, bearing_deg: float, rms_deg: float,
                       mod: str = "", snr: float = 0.0, is_real: bool = False):
        self._compass.set_scanning(False)
        self._compass.update_bearing(bearing_deg, rms_deg)
        self._info_lbl.setText(f"Kaynak: {mod or '---'}   |   SNR: {snr:.1f} dB")
        self._rms_lbl.setText(f"RMS Doğruluk: ±{rms_deg:.1f}°")
        self._set_source("real" if is_real else "sim")

    def set_scanning(self, scanning: bool):
        self._compass.set_scanning(scanning)
        if scanning:
            self._info_lbl.setText("Kaynak: ---   |   SNR: -- dB")
            self._set_source("none")

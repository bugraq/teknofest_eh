"""
Arabakışlı Karıştırma (Look-Through Jamming) Kontrol Paneli
Periyodik dinleme ↔ karıştırma döngüsü yönetimi — faz tabanlı otomatik devir.
"""

import math
import random
from collections import deque
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QGroupBox, QGridLayout, QSpinBox, QButtonGroup,
)
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QFont, QFontMetrics, QLinearGradient


# ─── Renk sabitler ──────────────────────────────────────────────────────────
C_DINLEME   = QColor("#3b82f6")   # mavi — dinleme fazı
C_KARAR     = QColor("#f59e0b")   # sarı — karar fazı
C_KARIŞTIRMA = QColor("#ef4444")  # kırmızı — karıştırma fazı
C_BG        = QColor("#0f172a")
C_BG2       = QColor("#1e293b")
C_BORDER    = QColor("#334155")


# ─── Faz göstergesi (üst 3 kutu) ─────────────────────────────────────────────
class _PhaseIndicator(QWidget):
    PHASES = ["DİNLEME", "KARAR", "KARIŞTIRMA"]
    COLORS = [C_DINLEME, C_KARAR, C_KARIŞTIRMA]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(44)
        self._active = -1   # hangi faz aktif (-1 = hiçbiri)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        self._labels: list[QLabel] = []
        for i, (name, col) in enumerate(zip(self.PHASES, self.COLORS)):
            lbl = QLabel(name)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
            lbl.setStyleSheet(
                f"border:1px solid {col.name()}; border-radius:6px; "
                f"color:{col.name()}; background:#0f172a; padding:4px;"
            )
            lay.addWidget(lbl)
            self._labels.append(lbl)

    def set_phase(self, phase_idx: int):
        self._active = phase_idx
        for i, (lbl, col) in enumerate(zip(self._labels, self.COLORS)):
            if i == phase_idx:
                lbl.setStyleSheet(
                    f"border:2px solid {col.name()}; border-radius:6px; "
                    f"color:#0f172a; background:{col.name()}; padding:4px; "
                    f"font-weight:bold;"
                )
            else:
                lbl.setStyleSheet(
                    f"border:1px solid {col.name()}; border-radius:6px; "
                    f"color:{col.darker(150).name()}; background:#0f172a; padding:4px;"
                )


# ─── Zaman çizelgesi (son N fazı boyalı olarak gösterir) ─────────────────────
class _TimelineWidget(QWidget):
    MAX_SEGS = 20

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(46)
        self.setMinimumWidth(200)
        # Her segment: (faz_idx, süre_ms)
        self._segs: deque = deque(maxlen=self.MAX_SEGS)

    def add_segment(self, phase_idx: int, duration_ms: int):
        self._segs.append((phase_idx, duration_ms))
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), C_BG2)

        if not self._segs:
            p.setPen(QPen(C_BORDER))
            p.drawRect(self.rect().adjusted(0, 0, -1, -1))
            p.end()
            return

        COLORS = [C_DINLEME, C_KARAR, C_KARIŞTIRMA]
        total_ms = sum(d for _, d in self._segs)
        if total_ms == 0:
            p.end()
            return

        w, h = self.width(), self.height()
        pad   = 4
        bar_h = 22
        bar_y = (h - bar_h) // 2

        x = pad
        for phase, dur in self._segs:
            seg_w = max(4, int((dur / total_ms) * (w - 2 * pad)))
            col   = COLORS[phase]
            p.fillRect(x, bar_y, seg_w, bar_h, col)
            # süre etiketi
            if seg_w > 24:
                p.setFont(QFont("Consolas", 7))
                p.setPen(QPen(QColor("#0f172a")))
                lbl = f"{dur}ms"
                fm  = QFontMetrics(QFont("Consolas", 7))
                lx  = x + (seg_w - fm.horizontalAdvance(lbl)) // 2
                p.drawText(lx, bar_y + bar_h // 2 + 4, lbl)
            x += seg_w

        p.setPen(QPen(C_BORDER, 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(pad, bar_y, w - 2 * pad, bar_h)

        # Alt aks: DINLEME / KARIŞTIRMA etiketi
        p.setFont(QFont("Consolas", 7))
        p.setPen(QPen(C_DINLEME))
        p.drawText(pad + 2, h - 4, "DİNL")
        p.setPen(QPen(C_KARIŞTIRMA))
        fm2 = QFontMetrics(QFont("Consolas", 7))
        p.drawText(w - pad - fm2.horizontalAdvance("JAM") - 2, h - 4, "JAM")
        p.end()


# ─── SNR mini grafik ──────────────────────────────────────────────────────────
class _SNRGraph(QWidget):
    MAX_PTS = 80

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(60)
        self._pts: deque = deque([0.0] * self.MAX_PTS, maxlen=self.MAX_PTS)

    def push(self, snr: float):
        self._pts.append(snr)
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), C_BG)

        w, h   = self.width(), self.height()
        pad    = 4
        vals   = list(self._pts)
        mn, mx = -5, 30
        rng    = mx - mn or 1

        # ızgara
        p.setPen(QPen(C_BORDER, 1))
        for db in [0, 10, 20]:
            y = h - pad - int((db - mn) / rng * (h - 2 * pad))
            p.drawLine(pad, y, w - pad, y)

        # Eşik çizgisi (-10 dB)
        thresh_y = h - pad - int((-10 - mn) / rng * (h - 2 * pad))   # aslında burada threshold
        # Biz detection threshold'u çizeceğiz
        # SNR grafiği
        pts = []
        for i, v in enumerate(vals):
            x = pad + int(i / (len(vals) - 1) * (w - 2 * pad)) if len(vals) > 1 else pad
            y = h - pad - int((v - mn) / rng * (h - 2 * pad))
            y = max(pad, min(h - pad, y))
            pts.append(QPointF(x, y))

        if len(pts) > 1:
            p.setPen(QPen(C_DINLEME, 1.5))
            for i in range(len(pts) - 1):
                p.drawLine(pts[i], pts[i + 1])

        # Eksen etiketi
        p.setFont(QFont("Consolas", 7))
        p.setPen(QPen(QColor("#64748b")))
        p.drawText(pad + 2, pad + 10, "SNR (dB)")
        p.end()


# ─── Ana panel ───────────────────────────────────────────────────────────────
class ArabakisliPanel(QWidget):
    PHASE_DINLEME    = 0
    PHASE_KARAR      = 1
    PHASE_KARIŞTIRMA = 2

    def __init__(self, state_manager=None):
        super().__init__()
        self.state_manager  = state_manager
        self._running       = False
        self._phase         = self.PHASE_DINLEME
        self._phase_elapsed = 0     # ms

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        # ── 1. Faz göstergesi ────────────────────────────────────────────
        self._phase_ind = _PhaseIndicator()
        root.addWidget(self._phase_ind)

        # ── 2. Zaman çizelgesi ───────────────────────────────────────────
        tl_box = self._gbox("KARIŞTIRMA ZAMANLAMASı", "#00d4ff")
        tl_lay = QVBoxLayout(tl_box)
        tl_lay.setContentsMargins(6, 18, 6, 6)
        tl_lay.setSpacing(6)

        self._timeline = _TimelineWidget()
        tl_lay.addWidget(self._timeline)

        self._snr_graph = _SNRGraph()
        tl_lay.addWidget(self._snr_graph)

        # Döngü sayacı
        self._cycle_lbl = QLabel("Döngü: 0  |  Toplam Süre: 0s")
        self._cycle_lbl.setStyleSheet(
            "color:#64748b; font-size:10px; font-family:Consolas; "
            "border:none; background:transparent;"
        )
        tl_lay.addWidget(self._cycle_lbl)
        root.addWidget(tl_box)

        # ── 3. Parametre Kontrolleri ─────────────────────────────────────
        param_box = self._gbox("DÖNGÜ PARAMETRELERİ", "#f59e0b")
        param_lay = QGridLayout(param_box)
        param_lay.setContentsMargins(10, 18, 10, 10)
        param_lay.setSpacing(6)

        param_lay.addWidget(self._lbl("Tespit Eşiği (dB):"), 0, 0)
        self._thresh_lbl = QLabel("-10 dB")
        self._thresh_lbl.setStyleSheet(
            "color:#f59e0b; font-family:Consolas; font-size:11px; "
            "border:none; background:transparent;"
        )
        param_lay.addWidget(self._thresh_lbl, 0, 1)

        self._thresh_slider = QSlider(Qt.Orientation.Horizontal)
        self._thresh_slider.setRange(-30, 0)
        self._thresh_slider.setValue(-10)
        self._thresh_slider.setStyleSheet(self._slider_style("#f59e0b"))
        self._thresh_slider.valueChanged.connect(
            lambda v: self._thresh_lbl.setText(f"{v} dB")
        )
        param_lay.addWidget(self._thresh_slider, 1, 0, 1, 2)

        param_lay.addWidget(self._lbl("Dinleme Süresi (ms):"), 2, 0)
        self._listen_spin = QSpinBox()
        self._listen_spin.setRange(10, 50)
        self._listen_spin.setValue(30)
        self._listen_spin.setSuffix(" ms")
        self._listen_spin.setStyleSheet(self._spin_style())
        param_lay.addWidget(self._listen_spin, 2, 1)

        param_lay.addWidget(self._lbl("Karıştırma Süresi (ms):"), 3, 0)
        self._jam_spin = QSpinBox()
        self._jam_spin.setRange(50, 200)
        self._jam_spin.setValue(100)
        self._jam_spin.setSuffix(" ms")
        self._jam_spin.setStyleSheet(self._spin_style())
        param_lay.addWidget(self._jam_spin, 3, 1)

        root.addWidget(param_box)

        # ── 4. Mod seçici (OTOMATİK / MANUEL) ───────────────────────────
        mode_box = self._gbox("ÇALIŞMA MODU", "#8b5cf6")
        mode_lay = QHBoxLayout(mode_box)
        mode_lay.setContentsMargins(10, 18, 10, 10)
        mode_lay.setSpacing(6)

        self._mode_grp = QButtonGroup(self)
        self._btn_auto = QPushButton("OTOMATİK")
        self._btn_manu = QPushButton("MANUEL")
        for i, btn in enumerate([self._btn_auto, self._btn_manu]):
            btn.setCheckable(True)
            btn.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
            btn.setFixedHeight(30)
            self._mode_grp.addButton(btn, i)
            mode_lay.addWidget(btn)
        self._btn_auto.setChecked(True)
        self._mode_grp.idToggled.connect(
            lambda bid, chk: self._refresh_mode_styles(bid) if chk else None
        )
        self._refresh_mode_styles(0)
        root.addWidget(mode_box)

        # ── 5. Sinyal varlığı + SDR durumu ───────────────────────────────
        status_box = self._gbox("SİNYAL & SDR DURUMU", "#64748b")
        status_lay = QGridLayout(status_box)
        status_lay.setContentsMargins(10, 18, 10, 10)
        status_lay.setSpacing(6)

        self._sig_lbl = QLabel("● SİNYAL: YOK")
        self._sig_lbl.setStyleSheet(
            "color:#334155; font-family:Consolas; font-size:12px; "
            "font-weight:bold; border:none; background:transparent;"
        )
        status_lay.addWidget(self._sig_lbl, 0, 0, 1, 2)

        for row, (name, val) in enumerate([
            ("ZMQ:", "BAĞLANMADI"),
            ("PLUTO RX:", "PASİF"),
            ("USRP TX:", "PASİF"),
        ], start=1):
            lbl_n = QLabel(name)
            lbl_n.setStyleSheet(
                "color:#64748b; font-size:11px; border:none; background:transparent;"
            )
            lbl_v = QLabel(val)
            lbl_v.setStyleSheet(
                "color:#ef4444; font-size:11px; font-family:Consolas; "
                "border:none; background:transparent;"
            )
            setattr(self, f"_sdr_{row}", lbl_v)
            status_lay.addWidget(lbl_n, row, 0)
            status_lay.addWidget(lbl_v, row, 1)
        root.addWidget(status_box)

        # ── 6. Başlat / Durdur ──────────────────────────────────────────
        self.btn_start = QPushButton("▶  SİSTEMİ ETKİNLEŞTİR")
        self.btn_start.setFixedHeight(44)
        self.btn_start.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.btn_start.setStyleSheet(
            "QPushButton { background:qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            "stop:0 #065f46,stop:1 #022c22); color:#10b981; "
            "border:2px solid #10b981; border-radius:8px; }"
            "QPushButton:hover { background:#047857; color:#6ee7b7; }"
            "QPushButton:disabled { background:#1e293b; color:#475569; border-color:#334155; }"
        )
        self.btn_start.clicked.connect(self._on_start)
        root.addWidget(self.btn_start)

        self.btn_stop = QPushButton("■  DURDUR")
        self.btn_stop.setFixedHeight(34)
        self.btn_stop.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet(
            "QPushButton { background:qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            "stop:0 #7f1d1d,stop:1 #450a0a); color:#ef4444; "
            "border:2px solid #ef4444; border-radius:8px; }"
            "QPushButton:hover { background:#991b1b; color:#fca5a5; }"
            "QPushButton:disabled { background:#1e293b; color:#475569; border-color:#334155; }"
        )
        self.btn_stop.clicked.connect(self._on_stop)
        root.addWidget(self.btn_stop)

        root.addStretch(1)

        # Faz döngü zamanlayıcısı (50ms tick)
        self._cycle_count   = 0
        self._total_time_ms = 0
        self._tick_timer    = QTimer(self)
        self._tick_timer.timeout.connect(self._tick)
        self._tick_timer.start(50)

        # SNR simülasyon zamanlayıcısı
        self._snr_timer = QTimer(self)
        self._snr_timer.timeout.connect(self._push_snr)
        self._snr_timer.start(150)
        self._fake_snr = 5.0

    # ── Stil yardımcıları ────────────────────────────────────────────────────
    @staticmethod
    def _gbox(title, accent) -> QGroupBox:
        b = QGroupBox(title)
        b.setStyleSheet(
            f"QGroupBox {{ border:1px solid #334155; border-radius:8px; "
            f"margin-top:12px; padding-top:8px; font-weight:bold; "
            f"color:{accent}; font-size:11px; font-family:Consolas; }}"
            f"QGroupBox::title {{ subcontrol-origin:margin; left:8px; padding:0 4px; }}"
        )
        return b

    @staticmethod
    def _lbl(text) -> QLabel:
        l = QLabel(text)
        l.setStyleSheet("color:#94a3b8; font-size:11px; border:none; background:transparent;")
        return l

    @staticmethod
    def _spin_style() -> str:
        return (
            "QSpinBox { background:#1e293b; color:#f8fafc; "
            "border:1px solid #475569; border-radius:4px; padding:3px; "
            "font-family:Consolas; font-size:11px; }"
        )

    @staticmethod
    def _slider_style(col: str) -> str:
        return (
            f"QSlider::groove:horizontal {{ height:6px; background:#334155; border-radius:3px; }}"
            f"QSlider::handle:horizontal {{ background:{col}; width:14px; height:14px; "
            f"margin:-4px 0; border-radius:7px; }}"
            f"QSlider::sub-page:horizontal {{ background:{col}; border-radius:3px; }}"
        )

    def _refresh_mode_styles(self, active_id: int):
        pairs = [(self._btn_auto, 0, "#8b5cf6"), (self._btn_manu, 1, "#f59e0b")]
        for btn, bid, col in pairs:
            if bid == active_id:
                btn.setStyleSheet(
                    f"QPushButton {{ background:#1e293b; color:{col}; "
                    f"border:2px solid {col}; border-radius:6px; "
                    f"font-family:Consolas; font-size:9pt; }}"
                )
            else:
                btn.setStyleSheet(
                    "QPushButton { background:#0f172a; color:#475569; "
                    "border:1px solid #334155; border-radius:6px; "
                    "font-family:Consolas; font-size:9pt; }"
                    "QPushButton:hover { color:#94a3b8; }"
                )

    # ── Faz döngü mantığı ────────────────────────────────────────────────────
    def _tick(self):
        if not self._running:
            return

        self._phase_elapsed   += 50
        self._total_time_ms   += 50

        listen_dur = self._listen_spin.value()
        jam_dur    = self._jam_spin.value()

        if self._phase == self.PHASE_DINLEME:
            if self._phase_elapsed >= listen_dur:
                self._advance_phase(self.PHASE_KARAR, listen_dur)

        elif self._phase == self.PHASE_KARAR:
            if self._phase_elapsed >= 200:  # karar fazı ~200ms
                self._advance_phase(self.PHASE_KARIŞTIRMA, 200)

        elif self._phase == self.PHASE_KARIŞTIRMA:
            if self._phase_elapsed >= jam_dur:
                self._cycle_count += 1
                self._advance_phase(self.PHASE_DINLEME, jam_dur)

        elapsed_s = self._total_time_ms // 1000
        self._cycle_lbl.setText(
            f"Döngü: {self._cycle_count}  |  Toplam Süre: {elapsed_s}s"
        )

    def _advance_phase(self, new_phase: int, elapsed_dur: int):
        self._timeline.add_segment(self._phase, elapsed_dur)
        self._phase         = new_phase
        self._phase_elapsed = 0
        self._phase_ind.set_phase(new_phase)

        # Sinyal varlığı simülasyonu
        if new_phase == self.PHASE_DINLEME:
            has_sig = random.random() > 0.3
            self._sig_lbl.setText(f"● SİNYAL: {'VAR' if has_sig else 'YOK'}")
            col = "#10b981" if has_sig else "#ef4444"
            self._sig_lbl.setStyleSheet(
                f"color:{col}; font-family:Consolas; font-size:12px; "
                f"font-weight:bold; border:none; background:transparent;"
            )

    def _push_snr(self):
        if self._running and self._phase == self.PHASE_DINLEME:
            self._fake_snr += random.uniform(-1.5, 1.5)
            self._fake_snr  = max(0, min(28, self._fake_snr))
        else:
            self._fake_snr = max(0, self._fake_snr - 1)
        self._snr_graph.push(self._fake_snr)

    # ── Buton aksiyonları ────────────────────────────────────────────────────
    def _on_start(self):
        self._running       = True
        self._phase         = self.PHASE_DINLEME
        self._phase_elapsed = 0
        self._cycle_count   = 0
        self._total_time_ms = 0
        self._phase_ind.set_phase(self.PHASE_DINLEME)
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        # SDR durumu simüle et
        for i, col in [(1, "#10b981"), (2, "#10b981"), (3, "#10b981")]:
            getattr(self, f"_sdr_{i}").setText("AKTİF")
            getattr(self, f"_sdr_{i}").setStyleSheet(
                f"color:{col}; font-size:11px; font-family:Consolas; "
                f"border:none; background:transparent;"
            )

    def _on_stop(self):
        self._running = False
        self._phase_ind.set_phase(-1)
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        for i in [1, 2, 3]:
            getattr(self, f"_sdr_{i}").setText("PASİF")
            getattr(self, f"_sdr_{i}").setStyleSheet(
                "color:#ef4444; font-size:11px; font-family:Consolas; "
                "border:none; background:transparent;"
            )

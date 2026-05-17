"""
Analog Telsiz Aldatma Kontrol Paneli
2-sütun profesyonel military HMI layout.
"""

import math
import random
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QGroupBox, QGridLayout, QListWidget, QListWidgetItem,
    QDoubleSpinBox, QComboBox, QButtonGroup, QCheckBox, QFrame,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QFont, QLinearGradient


C_AMBER  = QColor("#f97316")
C_GREEN  = QColor("#10b981")
C_CYAN   = QColor("#06b6d4")
C_BG     = QColor("#0a0f1e")
C_BG2    = QColor("#111827")
C_PANEL  = QColor("#1e293b")
C_BORDER = QColor("#334155")


# ─── Dalga formu önizleme ────────────────────────────────────────────────────
class _WaveformPreview(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(90)
        self._phase     = 0.0
        self._modtype   = "FM"
        self._active    = False

        self._anim = QTimer(self)
        self._anim.timeout.connect(self._step)
        self._anim.start(35)

    def set_mod(self, mod: str):
        self._modtype = mod

    def set_active(self, active: bool):
        self._active = active

    def _step(self):
        if self._active:
            self._phase += 0.12
        self.repaint()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), C_BG)

        w, h  = self.width(), self.height()
        cx_y  = h // 2
        pad   = 12

        # Grid yatay çizgiler
        p.setPen(QPen(QColor("#1e293b"), 1))
        for i in range(1, 4):
            y = int(h * i / 4)
            p.drawLine(pad, y, w - pad, y)

        N    = w - 2 * pad
        pts  = []
        for i in range(N):
            t = i / N * 6 * math.pi + self._phase
            if self._modtype == "FM":
                msg  = math.sin(t * 0.28)
                inst = t + 0.9 * msg
                y    = math.sin(inst) * (h // 2 - pad - 4)
            elif self._modtype == "AM":
                env = 0.45 + 0.55 * abs(math.sin(t * 0.22))
                y   = env * math.sin(t * 2.5) * (h // 2 - pad - 4)
            else:
                y = math.sin(t) * (h // 2 - pad - 4)
            pts.append(QPointF(pad + i, cx_y - y))

        # Sinyal rengi
        if self._active:
            grad = QLinearGradient(0, 0, w, 0)
            grad.setColorAt(0.0, QColor("#f97316"))
            grad.setColorAt(0.5, QColor("#fb923c"))
            grad.setColorAt(1.0, QColor("#f97316"))
            p.setPen(QPen(QBrush(grad), 1.8))
        else:
            p.setPen(QPen(QColor("#334155"), 1.2))

        for i in range(len(pts) - 1):
            p.drawLine(pts[i], pts[i + 1])

        # Merkez eksen
        p.setPen(QPen(QColor("#1e3a5f"), 1, Qt.PenStyle.DashLine))
        p.drawLine(pad, cx_y, w - pad, cx_y)

        # Sol etiket
        lbl = f"{'◉ CANLI TX' if self._active else '○ BEKLEMEDE'}  —  {self._modtype}"
        p.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        col = QColor("#f97316") if self._active else QColor("#475569")
        p.setPen(QPen(col))
        p.drawText(pad + 4, 16, lbl)

        # Sağ köşe: frekans bilgisi
        p.setFont(QFont("Consolas", 7))
        p.setPen(QPen(QColor("#475569")))
        p.drawText(w - 80, 16, "156.800 MHz")
        p.end()


# ─── VU Metre ─────────────────────────────────────────────────────────────────
class _VUMeter(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(32)
        self._level  = 0.0
        self._peak   = 0.0
        self._active = False

        self._t = QTimer(self)
        self._t.timeout.connect(self._step)
        self._t.start(55)

    def set_active(self, active: bool):
        self._active = active
        if not active:
            self._level = 0.0
            self._peak  = 0.0

    def _step(self):
        if self._active:
            target      = random.uniform(0.35, 0.95)
            self._level = self._level * 0.55 + target * 0.45
            self._peak  = max(self._peak * 0.985, self._level)
        else:
            self._level *= 0.80
            self._peak  *= 0.90
        self.repaint()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), C_BG)

        w, h  = self.width(), self.height()
        lbl_w = 36
        pad   = 4
        bx    = lbl_w + pad
        bw    = w - lbl_w - pad * 2
        bh    = h - pad * 2

        # Etiket
        p.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
        p.setPen(QPen(QColor("#475569")))
        p.drawText(pad, pad + bh // 2 + 4, "VU")

        # Arka plan
        p.fillRect(bx, pad, bw, bh, QColor("#0f172a"))
        p.setPen(QPen(C_BORDER, 1))
        p.drawRect(bx, pad, bw, bh)

        fill_w = int(bw * self._level)
        if fill_w > 0:
            grad = QLinearGradient(bx, 0, bx + bw, 0)
            grad.setColorAt(0.00, QColor("#10b981"))
            grad.setColorAt(0.60, QColor("#f59e0b"))
            grad.setColorAt(0.82, QColor("#ef4444"))
            grad.setColorAt(1.00, QColor("#dc2626"))
            p.fillRect(bx, pad + 1, fill_w, bh - 2, QBrush(grad))

        # Peak
        px = bx + int(bw * self._peak)
        p.setPen(QPen(QColor("#ffffff"), 2))
        p.drawLine(px, pad + 1, px, pad + bh - 1)

        # 0 dB marker
        mx = bx + int(bw * 0.85)
        p.setPen(QPen(QColor("#ef444466"), 1, Qt.PenStyle.DashLine))
        p.drawLine(mx, pad + 1, mx, pad + bh - 1)

        # dB skala
        p.setFont(QFont("Consolas", 6))
        p.setPen(QPen(QColor("#334155")))
        for frac, txt in [(0.0, "-∞"), (0.5, "-10"), (0.85, "0"), (1.0, "+3")]:
            xp = bx + int(bw * frac)
            p.drawText(xp - 6, pad + bh + 10, txt)

        p.end()


# ─── Yardımcı ─────────────────────────────────────────────────────────────────
def _section_header(text: str, accent: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setFixedHeight(22)
    lbl.setStyleSheet(
        f"color:{accent}; font-family:Consolas; font-size:9px; font-weight:bold; "
        f"letter-spacing:1px; border:none; background:transparent;"
    )
    return lbl


def _separator() -> QFrame:
    f = QFrame()
    f.setFixedHeight(1)
    f.setStyleSheet("QFrame { background:#1e293b; border:none; border-radius:0px; }")
    return f


def _input_style(accent: str = "#475569") -> str:
    return (
        f"QDoubleSpinBox, QSpinBox, QComboBox {{"
        f"  background:#111827; color:#e2e8f0; "
        f"  border:1px solid {accent}; border-radius:5px; "
        f"  padding:4px 6px; font-family:Consolas; font-size:11px; }}"
        f"QComboBox::drop-down {{ border:none; }}"
    )


# ─── Ana panel ────────────────────────────────────────────────────────────────
class TelsizAldatmaPanel(QWidget):

    _AUDIO_FILES = [
        "komuta_mesaj_01.wav",
        "telsiz_rapor_A.wav",
        "sahte_koordinat.wav",
        "gecmis_kayit_002.wav",
        "frekans_tarama.wav",
        "yanlis_hedef.wav",
        "acil_durum_sim.wav",
    ]

    def __init__(self, state_manager=None):
        super().__init__()
        self.state_manager = state_manager
        self._tx_active  = False
        self._rec_active = False
        self._rec_secs   = 0
        self._tx_secs    = 0

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Durum başlığı (tam genişlik) ──────────────────────────────────
        self._status_lbl = QLabel("◉   TELSİZ ALDATMA — PASİF")
        self._status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_lbl.setFixedHeight(32)
        self._status_lbl.setStyleSheet(
            "color:#475569; background:#0a0f1e; border:none; "
            "border-bottom:1px solid #1e293b; "
            "font-family:Consolas; font-size:11px; font-weight:bold; letter-spacing:1px;"
        )
        root.addWidget(self._status_lbl)

        # ── 2 SÜTUN ALAN ─────────────────────────────────────────────────
        body = QWidget()
        body_lay = QHBoxLayout(body)
        body_lay.setContentsMargins(12, 10, 12, 6)
        body_lay.setSpacing(12)

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # SOL SÜTUN  —  Ses Kütüphanesi + Dalga Formu
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        left = QWidget()
        left.setMinimumWidth(280)
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(0, 0, 0, 0)
        left_lay.setSpacing(8)

        # — Ses kütüphanesi bölümü
        left_lay.addWidget(_section_header("SES KÜTÜPHANESİ", C_AMBER.name()))

        self._file_list = QListWidget()
        self._file_list.setMinimumHeight(130)
        self._file_list.setStyleSheet(
            "QListWidget { background:#0a0f1e; color:#cbd5e1; "
            "border:1px solid #1e293b; border-radius:6px; "
            "font-family:Consolas; font-size:11px; padding:2px; }"
            "QListWidget::item { padding:4px 6px; border-radius:3px; }"
            "QListWidget::item:selected { background:#1e3a8a; color:#93c5fd; }"
            "QListWidget::item:hover { background:#1e293b; }"
        )
        for fn in self._AUDIO_FILES:
            item = QListWidgetItem(f"◈  {fn}")
            self._file_list.addItem(item)
        self._file_list.setCurrentRow(0)
        left_lay.addWidget(self._file_list)

        # — Kayıt butonları
        rec_row = QHBoxLayout()
        rec_row.setSpacing(6)

        self._btn_preview = self._mk_btn("▶  Önizle",      "#3b82f6")
        self._btn_preview_stop = self._mk_btn("⏹  Dur",    "#475569")
        self._btn_record  = self._mk_btn("●  Kayıt",       "#f97316")
        self._rec_dur_lbl = QLabel("00:00")
        self._rec_dur_lbl.setStyleSheet(
            "color:#f97316; font-family:Consolas; font-size:11px; "
            "border:none; background:transparent; min-width:36px;"
        )

        self._btn_preview.clicked.connect(self._on_preview)
        self._btn_preview_stop.clicked.connect(self._on_preview_stop)
        self._btn_record.clicked.connect(self._on_record)

        rec_row.addWidget(self._btn_preview)
        rec_row.addWidget(self._btn_preview_stop)
        rec_row.addWidget(self._btn_record)
        rec_row.addWidget(self._rec_dur_lbl)
        left_lay.addLayout(rec_row)

        left_lay.addWidget(_separator())

        # — Dalga formu önizleme
        left_lay.addWidget(_section_header("DALGA FORMU", C_AMBER.name()))
        self._waveform = _WaveformPreview()
        left_wf_frame = QFrame()
        left_wf_frame.setStyleSheet(
            "QFrame { background:#0a0f1e; border:1px solid #1e293b; border-radius:6px; }"
        )
        wf_lay = QVBoxLayout(left_wf_frame)
        wf_lay.setContentsMargins(0, 0, 0, 0)
        wf_lay.addWidget(self._waveform)
        left_lay.addWidget(left_wf_frame)

        # — VU Metre
        left_lay.addWidget(_section_header("VU METRE", "#10b981"))
        self._vu = _VUMeter()
        left_lay.addWidget(self._vu)

        # TX sayaç
        self._tx_cnt_lbl = QLabel("TX Süresi:  00:00:00")
        self._tx_cnt_lbl.setStyleSheet(
            "color:#10b981; font-family:Consolas; font-size:10px; "
            "border:none; background:transparent;"
        )
        left_lay.addWidget(self._tx_cnt_lbl)

        left_lay.addStretch()
        body_lay.addWidget(left)

        # Dikey ayraç
        vsep = QFrame()
        vsep.setFixedWidth(1)
        vsep.setStyleSheet("QFrame { background:#1e293b; border:none; border-radius:0px; }")
        body_lay.addWidget(vsep)

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # SAĞ SÜTUN  —  Frekans / Modülasyon / TX Kontrolü
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        right = QWidget()
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.setSpacing(8)

        # — Frekans & Modülasyon
        right_lay.addWidget(_section_header("FREKANS  &  MODÜLASYON", C_CYAN.name()))

        freq_grid = QGridLayout()
        freq_grid.setSpacing(6)
        freq_grid.setContentsMargins(0, 0, 0, 0)

        freq_grid.addWidget(self._lbl("Hedef Frekans (MHz):"), 0, 0)
        self._freq_combo = QComboBox()
        self._freq_combo.setEditable(False)
        self._freq_combo.addItems([
            "156.800 MHz  — VHF Deniz 16",
            "121.500 MHz  — Uçuş Acil",
            "243.000 MHz  — Askeri UHF",
            "406.000 MHz  — EPIRB",
            "162.550 MHz  — Hava Durumu",
            "155.340 MHz  — Taktik",
        ])
        self._freq_combo.setStyleSheet(
            "QComboBox { background:#111827; color:#e2e8f0; "
            "border:1px solid #334155; border-radius:5px; "
            "padding:4px 6px; font-family:Consolas; font-size:11px; }"
            "QComboBox::drop-down { border:none; padding-right:6px; }"
            "QComboBox QAbstractItemView { background:#111827; color:#e2e8f0; "
            "selection-background-color:#1e3a8a; }"
        )
        freq_grid.addWidget(self._freq_combo, 0, 1)

        self._btn_ai_detect = QPushButton("🧠  AI ile Frekans Tespit Et")
        self._btn_ai_detect.setFixedHeight(30)
        self._btn_ai_detect.setStyleSheet(
            "QPushButton { background:#0c1a4a; color:#60a5fa; "
            "border:1px solid #1d4ed8; border-radius:5px; "
            "font-family:Consolas; font-size:9px; font-weight:bold; }"
            "QPushButton:hover { background:#1d4ed8; color:#bfdbfe; }"
        )
        self._btn_ai_detect.clicked.connect(self._on_ai_detect)
        freq_grid.addWidget(self._btn_ai_detect, 1, 0, 1, 2)

        freq_grid.addWidget(self._lbl("Modülasyon Tipi:"), 2, 0)
        self._mod_combo = QComboBox()
        self._mod_combo.addItems([
            "FM  —  Frekans Modülasyonu",
            "AM  —  Genlik Modülasyonu",
            "SSB —  Tek Yan Bant",
            "WBFM — Geniş Bantlı FM",
        ])
        self._mod_combo.setStyleSheet(
            "QComboBox { background:#111827; color:#e2e8f0; "
            "border:1px solid #334155; border-radius:5px; "
            "padding:4px 6px; font-family:Consolas; font-size:11px; }"
            "QComboBox::drop-down { border:none; }"
        )
        self._mod_combo.currentIndexChanged.connect(self._on_mod_change)
        freq_grid.addWidget(self._mod_combo, 2, 1)

        self._ai_conf_lbl = QLabel("AI Tespit:  ---")
        self._ai_conf_lbl.setStyleSheet(
            "color:#8b5cf6; font-size:10px; font-family:Consolas; "
            "border:none; background:transparent;"
        )
        freq_grid.addWidget(self._ai_conf_lbl, 3, 0, 1, 2)
        right_lay.addLayout(freq_grid)

        right_lay.addWidget(_separator())

        # — Yayın Kontrolü
        right_lay.addWidget(_section_header("YAYIN KONTROLÜ", C_GREEN.name()))

        # Yöntem toggle
        meth_row = QHBoxLayout()
        meth_row.setSpacing(6)
        self._meth_grp   = QButtonGroup(self)
        self._btn_kayit  = QPushButton("KAYIT-TEKRAR")
        self._btn_sentez = QPushButton("SENTETİK SES")
        for i, btn in enumerate([self._btn_kayit, self._btn_sentez]):
            btn.setCheckable(True)
            btn.setFixedHeight(30)
            btn.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
            self._meth_grp.addButton(btn, i)
            meth_row.addWidget(btn)
        self._btn_kayit.setChecked(True)
        self._meth_grp.idToggled.connect(
            lambda bid, chk: self._refresh_meth_styles(bid) if chk else None
        )
        self._refresh_meth_styles(0)
        right_lay.addLayout(meth_row)

        # Güç
        pwr_row = QHBoxLayout()
        pwr_row.setSpacing(8)
        pwr_row.addWidget(self._lbl("Sinyal Gücü:"))
        self._pwr_lbl = QLabel("20 mW  /  13.0 dBm")
        self._pwr_lbl.setStyleSheet(
            "color:#f59e0b; font-family:Consolas; font-size:11px; "
            "border:none; background:transparent;"
        )
        pwr_row.addWidget(self._pwr_lbl)
        pwr_row.addStretch()
        right_lay.addLayout(pwr_row)

        self._pwr_slider = QSlider(Qt.Orientation.Horizontal)
        self._pwr_slider.setRange(1, 200)
        self._pwr_slider.setValue(20)
        self._pwr_slider.setStyleSheet(
            "QSlider::groove:horizontal { height:7px; background:#1e293b; "
            "border-radius:3px; border:1px solid #334155; }"
            "QSlider::handle:horizontal { background:#f59e0b; width:16px; "
            "height:16px; margin:-5px 0; border-radius:8px; }"
            "QSlider::sub-page:horizontal { background:#f59e0b; border-radius:3px; }"
        )
        self._pwr_slider.valueChanged.connect(self._on_power_change)
        right_lay.addWidget(self._pwr_slider)

        # Seçenekler (2 satır)
        opt_row1 = QHBoxLayout()
        opt_row2 = QHBoxLayout()
        self._chk_noise = QCheckBox("Gürültü Filtresi")
        self._chk_norm  = QCheckBox("Ses Normalizasyonu")
        self._chk_delay = QCheckBox("Gecikme Kompanzasyonu")
        self._chk_squelch = QCheckBox("Squelch Aktif")
        for chk in [self._chk_noise, self._chk_norm, self._chk_delay, self._chk_squelch]:
            chk.setStyleSheet(
                "QCheckBox { color:#94a3b8; font-size:11px; font-family:Consolas; "
                "border:none; background:transparent; }"
                "QCheckBox::indicator { width:13px; height:13px; "
                "border:1px solid #334155; border-radius:2px; background:#0f172a; }"
                "QCheckBox::indicator:checked { background:#3b82f6; border-color:#3b82f6; }"
            )
        self._chk_noise.setChecked(True)
        self._chk_norm.setChecked(True)
        self._chk_delay.setChecked(True)
        opt_row1.addWidget(self._chk_noise)
        opt_row1.addWidget(self._chk_norm)
        opt_row2.addWidget(self._chk_delay)
        opt_row2.addWidget(self._chk_squelch)
        right_lay.addLayout(opt_row1)
        right_lay.addLayout(opt_row2)

        right_lay.addStretch()
        body_lay.addWidget(right, stretch=1)

        root.addWidget(body, stretch=1)

        # ── Alt butonlar (tam genişlik) ────────────────────────────────────
        btn_bar = QWidget()
        btn_bar.setFixedHeight(62)
        btn_bar.setStyleSheet(
            "background:#0a0f1e; border-top:1px solid #1e293b;"
        )
        btn_lay = QHBoxLayout(btn_bar)
        btn_lay.setContentsMargins(12, 8, 12, 8)
        btn_lay.setSpacing(10)

        self.btn_start = QPushButton("▶   YAYINI BAŞLAT")
        self.btn_start.setFixedHeight(44)
        self.btn_start.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        self.btn_start.setStyleSheet(
            "QPushButton { background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #7c2d12, stop:1 #431407); color:#fb923c; "
            "border:2px solid #f97316; border-radius:8px; letter-spacing:2px; }"
            "QPushButton:hover { background:#c2410c; color:#fed7aa; }"
            "QPushButton:disabled { background:#1e293b; color:#334155; border-color:#334155; }"
        )
        self.btn_start.clicked.connect(self._on_tx_start)

        self.btn_stop = QPushButton("■   DURDUR")
        self.btn_stop.setFixedHeight(44)
        self.btn_stop.setFixedWidth(160)
        self.btn_stop.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet(
            "QPushButton { background:#1e293b; color:#334155; "
            "border:2px solid #334155; border-radius:8px; }"
            "QPushButton:enabled { background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #7f1d1d, stop:1 #450a0a); color:#ef4444; border-color:#ef4444; }"
            "QPushButton:enabled:hover { background:#991b1b; color:#fca5a5; }"
            "QPushButton:disabled { background:#1e293b; color:#334155; border-color:#334155; }"
        )
        self.btn_stop.clicked.connect(self._on_tx_stop)

        btn_lay.addWidget(self.btn_start, stretch=1)
        btn_lay.addWidget(self.btn_stop)
        root.addWidget(btn_bar)

        # Zamanlayıcılar
        self._rec_timer = QTimer(self)
        self._rec_timer.timeout.connect(self._rec_tick)

        self._tx_timer = QTimer(self)
        self._tx_timer.timeout.connect(self._tx_tick)

    # ── Yardımcılar ───────────────────────────────────────────────────────────
    @staticmethod
    def _mk_btn(text: str, color: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedHeight(28)
        btn.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        btn.setStyleSheet(
            f"QPushButton {{ background:#111827; color:{color}; "
            f"border:1px solid {color}44; border-radius:5px; padding:0 8px; }}"
            f"QPushButton:hover {{ background:{color}22; border-color:{color}; }}"
            f"QPushButton:pressed {{ background:{color}44; }}"
        )
        return btn

    @staticmethod
    def _lbl(text: str) -> QLabel:
        l = QLabel(text)
        l.setStyleSheet("color:#64748b; font-size:11px; border:none; background:transparent;")
        return l

    def _refresh_meth_styles(self, active: int):
        configs = {
            0: ("#3b82f6", self._btn_kayit),
            1: ("#10b981", self._btn_sentez),
        }
        for bid, (col, btn) in configs.items():
            if bid == active:
                btn.setStyleSheet(
                    f"QPushButton {{ background:#111827; color:{col}; "
                    f"border:2px solid {col}; border-radius:5px; "
                    f"font-family:Consolas; font-size:8pt; font-weight:bold; }}"
                )
            else:
                btn.setStyleSheet(
                    "QPushButton { background:#0a0f1e; color:#334155; "
                    "border:1px solid #1e293b; border-radius:5px; "
                    "font-family:Consolas; font-size:8pt; }"
                    "QPushButton:hover { color:#475569; }"
                )

    # ── Mantık ────────────────────────────────────────────────────────────────
    def _on_preview(self):
        self._waveform.set_active(True)

    def _on_preview_stop(self):
        self._waveform.set_active(False)

    def _on_record(self):
        if not self._rec_active:
            self._rec_active = True
            self._rec_secs   = 0
            self._btn_record.setText("⏹  Durdur")
            self._btn_record.setStyleSheet(
                "QPushButton { background:#7c2d12; color:#fb923c; "
                "border:1px solid #f97316; border-radius:5px; "
                "font-family:Consolas; font-size:8px; font-weight:bold; }"
            )
            self._rec_timer.start(1000)
        else:
            self._rec_active = False
            self._btn_record.setText("●  Kayıt")
            self._btn_record.setStyleSheet(
                "QPushButton { background:#111827; color:#f97316; "
                "border:1px solid #f9731644; border-radius:5px; "
                "font-family:Consolas; font-size:8px; font-weight:bold; }"
                "QPushButton:hover { background:#f9731622; border-color:#f97316; }"
            )
            self._rec_timer.stop()

    def _rec_tick(self):
        self._rec_secs += 1
        m, s = divmod(self._rec_secs, 60)
        self._rec_dur_lbl.setText(f"{m:02d}:{s:02d}")

    def _on_ai_detect(self):
        conf = random.uniform(87, 99)
        freqs_idx = random.randint(0, 5)
        mods_idx  = random.randint(0, 1)
        self._freq_combo.setCurrentIndex(freqs_idx)
        self._mod_combo.setCurrentIndex(mods_idx)
        self._ai_conf_lbl.setText(f"AI Tespit:  %{conf:.1f} güven  ✓")
        self._ai_conf_lbl.setStyleSheet(
            "color:#10b981; font-size:10px; font-family:Consolas; "
            "border:none; background:transparent;"
        )

    def _on_mod_change(self):
        mod_str = self._mod_combo.currentText()
        mod = "AM" if "AM" in mod_str else "FM"
        self._waveform.set_mod(mod)

    def _on_power_change(self, val: int):
        mw  = val
        dbm = round(10 * math.log10(mw), 1) if mw > 0 else -999
        self._pwr_lbl.setText(f"{mw} mW  /  {dbm} dBm")

    def _on_tx_start(self):
        self._tx_active = True
        self._tx_secs   = 0
        self._waveform.set_active(True)
        self._vu.set_active(True)
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self._status_lbl.setText("◉   TELSİZ ALDATMA — YAYIN AKTİF")
        self._status_lbl.setStyleSheet(
            "color:#fb923c; background:#7c2d12; border:none; "
            "border-bottom:2px solid #f97316; "
            "font-family:Consolas; font-size:11px; font-weight:bold; letter-spacing:1px;"
        )
        self._tx_timer.start(1000)

    def _on_tx_stop(self):
        self._tx_active = False
        self._waveform.set_active(False)
        self._vu.set_active(False)
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self._status_lbl.setText("◉   TELSİZ ALDATMA — PASİF")
        self._status_lbl.setStyleSheet(
            "color:#475569; background:#0a0f1e; border:none; "
            "border-bottom:1px solid #1e293b; "
            "font-family:Consolas; font-size:11px; font-weight:bold; letter-spacing:1px;"
        )
        self._tx_timer.stop()

    def _tx_tick(self):
        self._tx_secs += 1
        h, rem = divmod(self._tx_secs, 3600)
        m, s   = divmod(rem, 60)
        self._tx_cnt_lbl.setText(f"TX Süresi:  {h:02d}:{m:02d}:{s:02d}")

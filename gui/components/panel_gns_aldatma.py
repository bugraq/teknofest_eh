"""
GNS/GNSS Aldatma (Multi-Constellation Spoofing) Kontrol Paneli — kompakt versiyon
GPS, GLONASS, Galileo, BeiDou çoklu uydu sistemi aldatma arayüzü.
"""

import random
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QGridLayout, QCheckBox,
    QDoubleSpinBox, QComboBox, QProgressBar,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont


CONSTELLATIONS = {
    "GPS":     {"color": "#3b82f6", "freqs": ["L1-1575", "L2-1228", "L5-1176"], "sats": 31},
    "GLONASS": {"color": "#10b981", "freqs": ["L1-1602", "L2-1246"],              "sats": 24},
    "GALİLEO": {"color": "#f59e0b", "freqs": ["E1-1575", "E5a-1176", "E5b-1207"], "sats": 30},
    "BEİDOU":  {"color": "#8b5cf6", "freqs": ["B1-1561", "B2-1207", "B3-1269"],   "sats": 48},
}


def _gbox(title: str, accent: str) -> QGroupBox:
    box = QGroupBox(title)
    box.setStyleSheet(
        f"QGroupBox {{ border:1px solid #1e293b; border-radius:6px; "
        f"margin-top:8px; padding-top:6px; font-weight:bold; "
        f"color:{accent}; font-size:10px; font-family:Consolas; }}"
        f"QGroupBox::title {{ subcontrol-origin:margin; left:8px; padding:0 3px; }}"
    )
    return box


def _lbl(text: str) -> QLabel:
    l = QLabel(text)
    l.setStyleSheet("color:#64748b; font-size:10px; border:none; background:transparent;")
    return l


def _spin_style() -> str:
    return (
        "QDoubleSpinBox, QSpinBox { background:#111827; color:#e2e8f0; "
        "border:1px solid #334155; border-radius:4px; padding:2px 4px; "
        "font-family:Consolas; font-size:10px; }"
    )


# ─── Konstelasyon satırı ──────────────────────────────────────────────────────
class _ConstellationRow(QWidget):
    def __init__(self, name: str, info: dict, parent=None):
        super().__init__(parent)
        self.name  = name
        self._info = info
        uid = name.replace("İ", "I").replace("Ü", "U")
        self.setObjectName(f"ConsRow_{uid}")
        self.setStyleSheet(
            f"QWidget#ConsRow_{uid} {{ "
            f"background-color:#0a0f1e; "
            f"border:1px solid #1e293b; border-radius:4px; }}"
        )
        self.setFixedHeight(28)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 2, 6, 2)
        lay.setSpacing(6)

        self._chk = QCheckBox(name)
        self._chk.setStyleSheet(
            f"QCheckBox {{ color:{info['color']}; font-family:Consolas; "
            f"font-size:10px; font-weight:bold; border:none; background:transparent; }}"
            f"QCheckBox::indicator {{ width:12px; height:12px; "
            f"border:1px solid {info['color']}66; border-radius:2px; background:#0a0f1e; }}"
            f"QCheckBox::indicator:checked {{ background:{info['color']}; border-color:{info['color']}; }}"
        )
        self._chk.setFixedWidth(72)
        self._chk.stateChanged.connect(self._on_toggle)
        lay.addWidget(self._chk)

        self._freq_combo = QComboBox()
        self._freq_combo.addItems(info["freqs"])
        self._freq_combo.setEnabled(False)
        self._freq_combo.setFixedHeight(20)
        self._freq_combo.setStyleSheet(
            "QComboBox { background:#111827; color:#cbd5e1; border:1px solid #334155; "
            "border-radius:3px; padding:1px 4px; font-family:Consolas; font-size:9px; }"
            "QComboBox::drop-down { border:none; width:14px; }"
            "QComboBox QAbstractItemView { background:#111827; color:#e2e8f0; "
            "selection-background-color:#1e3a8a; font-size:9px; }"
        )
        lay.addWidget(self._freq_combo, stretch=1)

        self._sat_lbl = QLabel(f"{info['sats']}SV")
        self._sat_lbl.setFixedWidth(32)
        self._sat_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._sat_lbl.setStyleSheet(
            "color:#334155; font-size:9px; border:none; "
            "background:transparent; font-family:Consolas;"
        )
        lay.addWidget(self._sat_lbl)

        self._dot = QLabel("●")
        self._dot.setFixedWidth(14)
        self._dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._dot.setStyleSheet("color:#1e293b; font-size:11px; border:none; background:transparent;")
        lay.addWidget(self._dot)

    def _on_toggle(self, state: int):
        enabled = state == Qt.CheckState.Checked.value
        self._freq_combo.setEnabled(enabled)
        col = self._info["color"] if enabled else "#1e293b"
        self._dot.setStyleSheet(f"color:{col}; font-size:11px; border:none; background:transparent;")
        self._sat_lbl.setStyleSheet(
            f"color:{'#64748b' if enabled else '#334155'}; font-size:9px; "
            f"border:none; background:transparent; font-family:Consolas;"
        )

    def is_active(self) -> bool:
        return self._chk.isChecked()

    def get_freq(self) -> str:
        return self._freq_combo.currentText()

    def set_spoof_active(self, active: bool):
        col = "#ef4444" if (active and self._chk.isChecked()) \
              else (self._info["color"] if self._chk.isChecked() else "#1e293b")
        self._dot.setStyleSheet(f"color:{col}; font-size:11px; border:none; background:transparent;")


# ─── Sinyal gücü çubuğu ──────────────────────────────────────────────────────
class _SignalBar(QWidget):
    def __init__(self, label: str, color: str, parent=None):
        super().__init__(parent)
        self.setFixedHeight(16)
        self.setStyleSheet("background:transparent; border:none;")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(5)

        lbl = QLabel(label)
        lbl.setFixedWidth(56)
        lbl.setStyleSheet(
            f"color:{color}; font-size:9px; font-family:Consolas; "
            f"border:none; background:transparent;"
        )
        lay.addWidget(lbl)

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(6)
        self._bar.setStyleSheet(
            f"QProgressBar {{ background:#1e293b; border-radius:3px; border:none; }}"
            f"QProgressBar::chunk {{ background:{color}; border-radius:3px; }}"
        )
        lay.addWidget(self._bar)

        self._val = QLabel("---")
        self._val.setFixedWidth(58)
        self._val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._val.setStyleSheet(
            f"color:{color}66; font-size:9px; font-family:Consolas; "
            f"border:none; background:transparent;"
        )
        lay.addWidget(self._val)

    def set_value(self, pct: int, txt: str):
        self._bar.setValue(pct)
        self._val.setText(txt)


# ─── Ana panel ────────────────────────────────────────────────────────────────
class GNSAldatmaPanel(QWidget):

    def __init__(self, state_manager=None):
        super().__init__()
        self.state_manager = state_manager
        self._active = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(4)

        # ── Durum başlığı ────────────────────────────────────────────────
        self._status_lbl = QLabel("◈   GNSS ALDATMA — PASİF")
        self._status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_lbl.setFixedHeight(24)
        self._status_lbl.setStyleSheet(
            "color:#475569; background:#0a0f1e; border:none; "
            "border-bottom:1px solid #1e293b; "
            "font-family:Consolas; font-size:9px; font-weight:bold; letter-spacing:1px;"
        )
        root.addWidget(self._status_lbl)

        # ── Konstelasyon seçici ──────────────────────────────────────────
        cons_box = _gbox("HEDEF KONSTELASYONlar", "#06b6d4")
        cons_lay = QVBoxLayout(cons_box)
        cons_lay.setContentsMargins(6, 14, 6, 6)
        cons_lay.setSpacing(3)

        self._cons_rows: dict[str, _ConstellationRow] = {}
        for name, info in CONSTELLATIONS.items():
            row = _ConstellationRow(name, info)
            self._cons_rows[name] = row
            cons_lay.addWidget(row)

        self._cons_rows["GPS"]._chk.setChecked(True)
        root.addWidget(cons_box)

        # ── Aldatma modu (2 sütun kompakt grid) ─────────────────────────
        mode_box = _gbox("ALDATMA MODU", "#8b5cf6")
        mode_lay = QGridLayout(mode_box)
        mode_lay.setContentsMargins(8, 14, 8, 6)
        mode_lay.setSpacing(4)
        mode_lay.setColumnStretch(1, 1)

        mode_lay.addWidget(_lbl("Mod:"), 0, 0)
        self._mode_combo = QComboBox()
        self._mode_combo.addItems([
            "Konum Sahteciliği",
            "Zaman Sahteciliği",
            "Hız Yanıltma",
            "Sinyal Tekrar (Meaconing)",
            "Bastırma + Yeniden Yayın",
        ])
        self._mode_combo.setStyleSheet(
            "QComboBox { background:#111827; color:#e2e8f0; border:1px solid #334155; "
            "border-radius:4px; padding:2px 4px; font-family:Consolas; font-size:10px; }"
            "QComboBox::drop-down { border:none; }"
            "QComboBox QAbstractItemView { background:#111827; color:#e2e8f0; "
            "selection-background-color:#1e3a8a; }"
        )
        mode_lay.addWidget(self._mode_combo, 0, 1)

        mode_lay.addWidget(_lbl("Konum Δ:"), 1, 0)
        self._pos_offset = QDoubleSpinBox()
        self._pos_offset.setRange(0, 50000)
        self._pos_offset.setValue(500)
        self._pos_offset.setSuffix(" m")
        self._pos_offset.setStyleSheet(_spin_style())
        mode_lay.addWidget(self._pos_offset, 1, 1)

        mode_lay.addWidget(_lbl("Zaman Δ:"), 2, 0)
        self._time_offset = QDoubleSpinBox()
        self._time_offset.setRange(-1000, 1000)
        self._time_offset.setValue(0)
        self._time_offset.setSuffix(" ms")
        self._time_offset.setStyleSheet(_spin_style())
        mode_lay.addWidget(self._time_offset, 2, 1)
        root.addWidget(mode_box)

        # ── Sinyal güçleri ───────────────────────────────────────────────
        pwr_box = _gbox("SİNYAL GÜÇLERİ", "#f59e0b")
        pwr_lay = QVBoxLayout(pwr_box)
        pwr_lay.setContentsMargins(8, 14, 8, 6)
        pwr_lay.setSpacing(3)

        self._sig_bars: dict[str, _SignalBar] = {}
        for name, info in CONSTELLATIONS.items():
            bar = _SignalBar(name, info["color"])
            self._sig_bars[name] = bar
            pwr_lay.addWidget(bar)
        root.addWidget(pwr_box)

        # ── Gelişmiş seçenekler (yatay 3'lü) ────────────────────────────
        opt_box = _gbox("GELİŞMİŞ SEÇENEKLER", "#475569")
        opt_lay = QHBoxLayout(opt_box)
        opt_lay.setContentsMargins(8, 14, 8, 6)
        opt_lay.setSpacing(12)

        chk_style = (
            "QCheckBox { color:#64748b; font-size:9px; font-family:Consolas; "
            "border:none; background:transparent; }"
            "QCheckBox::indicator { width:11px; height:11px; "
            "border:1px solid #334155; border-radius:2px; background:#0a0f1e; }"
            "QCheckBox::indicator:checked { background:#475569; border-color:#64748b; }"
        )
        self._chk_nav  = QCheckBox("Nav Mesajı")
        self._chk_dop  = QCheckBox("Doppler")
        self._chk_sync = QCheckBox("Çoklu Sync")
        for chk in [self._chk_nav, self._chk_dop, self._chk_sync]:
            chk.setStyleSheet(chk_style)
            opt_lay.addWidget(chk)
        self._chk_nav.setChecked(True)
        self._chk_sync.setChecked(True)
        root.addWidget(opt_box)

        # ── Başlat / Durdur ──────────────────────────────────────────────
        self.btn_start = QPushButton("▶  GNSS ALDATMAYI BAŞLAT")
        self.btn_start.setFixedHeight(38)
        self.btn_start.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        self.btn_start.setStyleSheet(
            "QPushButton { background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #4c1d95,stop:1 #1e0a3c); color:#c4b5fd; "
            "border:2px solid #7c3aed; border-radius:7px; letter-spacing:1px; }"
            "QPushButton:hover { background:#5b21b6; color:#ddd6fe; }"
            "QPushButton:disabled { background:#1e293b; color:#334155; border-color:#334155; }"
        )
        self.btn_start.clicked.connect(self._on_start)
        root.addWidget(self.btn_start)

        self.btn_stop = QPushButton("■  DURDUR")
        self.btn_stop.setFixedHeight(28)
        self.btn_stop.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet(
            "QPushButton { background:#1e293b; color:#334155; "
            "border:1px solid #334155; border-radius:7px; }"
            "QPushButton:enabled { background:#450a0a; color:#ef4444; border-color:#ef4444; }"
            "QPushButton:enabled:hover { background:#7f1d1d; color:#fca5a5; }"
            "QPushButton:disabled { background:#1e293b; color:#334155; border-color:#334155; }"
        )
        self.btn_stop.clicked.connect(self._on_stop)
        root.addWidget(self.btn_stop)

        root.addStretch(1)

        self._sim_timer = QTimer(self)
        self._sim_timer.timeout.connect(self._update_sig_bars)
        self._sim_timer.start(800)

    def _update_sig_bars(self):
        for name, row in self._cons_rows.items():
            bar = self._sig_bars[name]
            if row.is_active() and self._active:
                pct = random.randint(55, 90)
                bar.set_value(pct, f"{round(-130 + pct*0.3, 1)}dBm")
            elif row.is_active():
                pct = random.randint(10, 30)
                bar.set_value(pct, f"{round(-150 + pct*0.2, 1)}dBm")
            else:
                bar.set_value(0, "---")

    def _get_active(self) -> list[str]:
        return [n for n, r in self._cons_rows.items() if r.is_active()]

    def _on_start(self):
        active = self._get_active()
        if not active:
            return
        self._active = True
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        tag = "+".join(active)
        self._status_lbl.setText(f"◈   GNSS ALDATMA — AKTİF  [ {tag} ]")
        self._status_lbl.setStyleSheet(
            "color:#ef4444; background:#450a0a; border:none; "
            "border-bottom:2px solid #ef4444; "
            "font-family:Consolas; font-size:9px; font-weight:bold; letter-spacing:1px;"
        )
        for row in self._cons_rows.values():
            row.set_spoof_active(True)
        if self.state_manager and hasattr(self.state_manager, "update_gns_spoof_state"):
            self.state_manager.update_gns_spoof_state(
                True, active, self._mode_combo.currentText(),
                self._pos_offset.value(), self._time_offset.value(),
            )

    def _on_stop(self):
        self._active = False
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self._status_lbl.setText("◈   GNSS ALDATMA — PASİF")
        self._status_lbl.setStyleSheet(
            "color:#475569; background:#0a0f1e; border:none; "
            "border-bottom:1px solid #1e293b; "
            "font-family:Consolas; font-size:9px; font-weight:bold; letter-spacing:1px;"
        )
        for row in self._cons_rows.values():
            row.set_spoof_active(False)
        if self.state_manager and hasattr(self.state_manager, "update_gns_spoof_state"):
            self.state_manager.update_gns_spoof_state(False, [], "", 0, 0)

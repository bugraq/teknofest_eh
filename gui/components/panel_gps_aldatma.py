"""
GPS Aldatma (Spoofing) Kontrol Paneli — kompakt versiyon
"""

import random
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QGroupBox, QGridLayout, QCheckBox, QSpinBox,
    QDoubleSpinBox, QComboBox,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont


# ─── Stil yardımcıları ────────────────────────────────────────────────────────
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


def _input_style() -> str:
    return (
        "QDoubleSpinBox, QSpinBox { background:#111827; color:#e2e8f0; "
        "border:1px solid #334155; border-radius:4px; padding:2px 4px; "
        "font-family:Consolas; font-size:10px; }"
    )


def _combo_style() -> str:
    return (
        "QComboBox { background:#111827; color:#e2e8f0; border:1px solid #334155; "
        "border-radius:4px; padding:2px 4px; font-family:Consolas; font-size:10px; }"
        "QComboBox::drop-down { border:none; }"
    )


# ─── Koordinat çifti göstergesi ──────────────────────────────────────────────
# QWidget (not QFrame) ve set_coords() metodu — Qt çakışmalarını önlemek için
class _CoordDisplay(QWidget):
    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        self.setObjectName("CoordDisplay")
        self.setFixedHeight(40)
        self.setStyleSheet(
            "QWidget#CoordDisplay { background-color:#0a0f1e; "
            "border:1px solid #1e293b; border-radius:4px; }"
        )

        lay = QVBoxLayout(self)
        lay.setContentsMargins(7, 3, 7, 3)
        lay.setSpacing(1)

        hdr = QLabel(label)
        hdr.setStyleSheet(
            "color:#334155; font-size:8px; font-weight:bold; letter-spacing:1px; "
            "border:none; background:transparent; font-family:Consolas;"
        )
        lay.addWidget(hdr)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        self._real_lbl = QLabel("---")
        self._real_lbl.setStyleSheet(
            "color:#3b82f6; font-size:10px; font-family:Consolas; "
            "border:none; background:transparent;"
        )

        arrow = QLabel("→")
        arrow.setFixedWidth(14)
        arrow.setStyleSheet("color:#1e3a5f; border:none; background:transparent; font-size:11px;")

        self._fake_lbl = QLabel("---")
        self._fake_lbl.setStyleSheet(
            "color:#ef4444; font-size:10px; font-family:Consolas; "
            "border:none; background:transparent;"
        )

        row.addWidget(self._real_lbl)
        row.addWidget(arrow)
        row.addWidget(self._fake_lbl)
        row.addStretch()
        lay.addLayout(row)

    def set_coords(self, real: str, fake: str):
        self._real_lbl.setText(real)
        self._fake_lbl.setText(fake)


# ─── Ana panel ────────────────────────────────────────────────────────────────
class GPSAldatmaPanel(QWidget):

    BASE_LAT = 39.9208
    BASE_LON = 32.8541
    BASE_ALT = 890.0

    def __init__(self, state_manager=None):
        super().__init__()
        self.state_manager = state_manager
        self._active  = False
        self._sim_lat = self.BASE_LAT
        self._sim_lon = self.BASE_LON

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(4)

        # ── Durum başlığı ────────────────────────────────────────────────
        self._status_lbl = QLabel("◉   GPS ALDATMA — PASİF")
        self._status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_lbl.setFixedHeight(24)
        self._status_lbl.setStyleSheet(
            "color:#475569; background:#0a0f1e; border:none; "
            "border-bottom:1px solid #1e293b; "
            "font-family:Consolas; font-size:9px; font-weight:bold; letter-spacing:1px;"
        )
        root.addWidget(self._status_lbl)

        # ── Koordinat göstergeleri ───────────────────────────────────────
        coord_box = _gbox("KONUM BİLGİSİ", "#3b82f6")
        coord_lay = QVBoxLayout(coord_box)
        coord_lay.setContentsMargins(6, 14, 6, 6)
        coord_lay.setSpacing(3)

        self._lat_disp = _CoordDisplay("ENLEM (LAT)")
        self._lon_disp = _CoordDisplay("BOYLAM (LON)")
        self._alt_disp = _CoordDisplay("YÜKSEKLİK (ALT)")
        coord_lay.addWidget(self._lat_disp)
        coord_lay.addWidget(self._lon_disp)
        coord_lay.addWidget(self._alt_disp)
        root.addWidget(coord_box)

        # ── Sapma ayarları ───────────────────────────────────────────────
        offset_box = _gbox("KONUM SAPMASI (OFFSET)", "#f59e0b")
        offset_lay = QGridLayout(offset_box)
        offset_lay.setContentsMargins(8, 14, 8, 6)
        offset_lay.setSpacing(4)
        offset_lay.setColumnStretch(1, 1)

        offset_lay.addWidget(_lbl("Enlem Δ (°):"), 0, 0)
        self._lat_spin = QDoubleSpinBox()
        self._lat_spin.setRange(-5.0, 5.0)
        self._lat_spin.setSingleStep(0.01)
        self._lat_spin.setDecimals(4)
        self._lat_spin.setValue(0.05)
        self._lat_spin.setStyleSheet(_input_style())
        self._lat_spin.valueChanged.connect(self._on_offset_change)
        offset_lay.addWidget(self._lat_spin, 0, 1)

        offset_lay.addWidget(_lbl("Boylam Δ (°):"), 1, 0)
        self._lon_spin = QDoubleSpinBox()
        self._lon_spin.setRange(-5.0, 5.0)
        self._lon_spin.setSingleStep(0.01)
        self._lon_spin.setDecimals(4)
        self._lon_spin.setValue(0.08)
        self._lon_spin.setStyleSheet(_input_style())
        self._lon_spin.valueChanged.connect(self._on_offset_change)
        offset_lay.addWidget(self._lon_spin, 1, 1)

        offset_lay.addWidget(_lbl("Yükseklik Δ (m):"), 2, 0)
        self._alt_spin = QDoubleSpinBox()
        self._alt_spin.setRange(-500.0, 5000.0)
        self._alt_spin.setSingleStep(10.0)
        self._alt_spin.setDecimals(1)
        self._alt_spin.setValue(0.0)
        self._alt_spin.setStyleSheet(_input_style())
        self._alt_spin.valueChanged.connect(self._on_offset_change)
        offset_lay.addWidget(self._alt_spin, 2, 1)
        root.addWidget(offset_box)

        # ── Sinyal parametreleri ─────────────────────────────────────────
        sig_box = _gbox("SİNYAL PARAMETRELERİ", "#8b5cf6")
        sig_lay = QGridLayout(sig_box)
        sig_lay.setContentsMargins(8, 14, 8, 6)
        sig_lay.setSpacing(4)
        sig_lay.setColumnStretch(1, 1)

        sig_lay.addWidget(_lbl("Bant:"), 0, 0)
        self._band_combo = QComboBox()
        self._band_combo.addItems(["L1 — 1575.42 MHz", "L2 — 1227.60 MHz", "L5 — 1176.45 MHz"])
        self._band_combo.setStyleSheet(_combo_style())
        sig_lay.addWidget(self._band_combo, 0, 1)

        sig_lay.addWidget(_lbl("PRN Sayısı:"), 1, 0)
        self._prn_spin = QSpinBox()
        self._prn_spin.setRange(4, 12)
        self._prn_spin.setValue(8)
        self._prn_spin.setStyleSheet(_input_style())
        sig_lay.addWidget(self._prn_spin, 1, 1)

        pwr_row = QHBoxLayout()
        pwr_row.setSpacing(6)
        pwr_row.addWidget(_lbl("Sinyal Gücü:"))
        self._pwr_lbl = QLabel("-130 dBm")
        self._pwr_lbl.setStyleSheet(
            "color:#f59e0b; font-family:Consolas; font-size:10px; "
            "border:none; background:transparent;"
        )
        pwr_row.addWidget(self._pwr_lbl)
        pwr_row.addStretch()
        sig_lay.addLayout(pwr_row, 2, 0, 1, 2)

        self._pwr_slider = QSlider(Qt.Orientation.Horizontal)
        self._pwr_slider.setRange(-160, -100)
        self._pwr_slider.setValue(-130)
        self._pwr_slider.setFixedHeight(16)
        self._pwr_slider.setStyleSheet(
            "QSlider::groove:horizontal { height:5px; background:#1e293b; border-radius:2px; }"
            "QSlider::handle:horizontal { background:#8b5cf6; width:13px; "
            "height:13px; margin:-4px 0; border-radius:6px; }"
            "QSlider::sub-page:horizontal { background:#8b5cf6; border-radius:2px; }"
        )
        self._pwr_slider.valueChanged.connect(lambda v: self._pwr_lbl.setText(f"{v} dBm"))
        sig_lay.addWidget(self._pwr_slider, 3, 0, 1, 2)

        sig_lay.addWidget(_lbl("Zamanlama Δ:"), 4, 0)
        self._timing_spin = QSpinBox()
        self._timing_spin.setRange(-500, 500)
        self._timing_spin.setValue(0)
        self._timing_spin.setSuffix(" ns")
        self._timing_spin.setStyleSheet(_input_style())
        sig_lay.addWidget(self._timing_spin, 4, 1)
        root.addWidget(sig_box)

        # ── Seçenekler ───────────────────────────────────────────────────
        opt_box = _gbox("ALDATMA SEÇENEKLERİ", "#06b6d4")
        opt_lay = QVBoxLayout(opt_box)
        opt_lay.setContentsMargins(8, 14, 8, 6)
        opt_lay.setSpacing(2)

        self._chk_drift     = QCheckBox("Kademeli Konum Kayması (Drift)")
        self._chk_multipath = QCheckBox("Çoklu Yol Simülasyonu (Multipath)")
        self._chk_replay    = QCheckBox("Sinyal Tekrar Yayını (Replay)")
        chk_style = (
            "QCheckBox { color:#94a3b8; font-size:10px; font-family:Consolas; "
            "border:none; background:transparent; }"
            "QCheckBox::indicator { width:12px; height:12px; "
            "border:1px solid #334155; border-radius:2px; background:#0a0f1e; }"
            "QCheckBox::indicator:checked { background:#3b82f6; border-color:#3b82f6; }"
        )
        for chk in [self._chk_drift, self._chk_multipath, self._chk_replay]:
            chk.setStyleSheet(chk_style)
            opt_lay.addWidget(chk)
        self._chk_drift.setChecked(True)
        root.addWidget(opt_box)

        # ── Başlat / Durdur ──────────────────────────────────────────────
        self.btn_start = QPushButton("▶  GPS ALDATMAYI BAŞLAT")
        self.btn_start.setFixedHeight(38)
        self.btn_start.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        self.btn_start.setStyleSheet(
            "QPushButton { background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #1e3a8a,stop:1 #0c1a4a); color:#60a5fa; "
            "border:2px solid #3b82f6; border-radius:7px; letter-spacing:1px; }"
            "QPushButton:hover { background:#1d4ed8; color:#bfdbfe; }"
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

        self._refresh_coord_display()

        self._drift_timer = QTimer(self)
        self._drift_timer.timeout.connect(self._apply_drift)
        self._drift_timer.start(1500)

    # ── Mantık ────────────────────────────────────────────────────────────────
    def _on_offset_change(self):
        self._sim_lat = self.BASE_LAT + self._lat_spin.value()
        self._sim_lon = self.BASE_LON + self._lon_spin.value()
        self._refresh_coord_display()

    def _refresh_coord_display(self):
        real_lat = f"{self.BASE_LAT:.4f}°N"
        real_lon = f"{self.BASE_LON:.4f}°E"
        real_alt = f"{self.BASE_ALT:.0f} m"
        fake_lat = f"{self._sim_lat:.4f}°N"
        fake_lon = f"{self._sim_lon:.4f}°E"
        fake_alt = f"{self.BASE_ALT + self._alt_spin.value():.0f} m"
        self._lat_disp.set_coords(real_lat, fake_lat)
        self._lon_disp.set_coords(real_lon, fake_lon)
        self._alt_disp.set_coords(real_alt, fake_alt)

    def _apply_drift(self):
        if self._active and self._chk_drift.isChecked():
            self._sim_lat += random.uniform(-0.0002, 0.0002)
            self._sim_lon += random.uniform(-0.0002, 0.0002)
            self._refresh_coord_display()

    def _on_start(self):
        self._active = True
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self._status_lbl.setText("◉   GPS ALDATMA — AKTİF")
        self._status_lbl.setStyleSheet(
            "color:#ef4444; background:#450a0a; border:none; "
            "border-bottom:2px solid #ef4444; "
            "font-family:Consolas; font-size:9px; font-weight:bold; letter-spacing:1px;"
        )
        if self.state_manager and hasattr(self.state_manager, "update_gps_spoof_state"):
            self.state_manager.update_gps_spoof_state(
                True, self._sim_lat, self._sim_lon,
                self.BASE_ALT + self._alt_spin.value()
            )

    def _on_stop(self):
        self._active = False
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self._status_lbl.setText("◉   GPS ALDATMA — PASİF")
        self._status_lbl.setStyleSheet(
            "color:#475569; background:#0a0f1e; border:none; "
            "border-bottom:1px solid #1e293b; "
            "font-family:Consolas; font-size:9px; font-weight:bold; letter-spacing:1px;"
        )
        if self.state_manager and hasattr(self.state_manager, "update_gps_spoof_state"):
            self.state_manager.update_gps_spoof_state(False, 0, 0, 0)

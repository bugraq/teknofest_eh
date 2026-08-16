"""
Gercek bir u-blox (veya NMEA uyumlu herhangi bir) GPS/GNSS alicisindan
$GPGGA / $GNGGA cumlelerini okuyup fix konumunu cikaran arka plan okuyucusu.

GPS donanimi takili olmasa, port yanlis olsa veya fix hic gelmese bile
GUI'nin sorunsuz acilabilmesi icin hicbir hata disariya firlatilmaz;
boyle durumlarda get_position() sessizce MANUEL (Elazig) konumuna duser.
"""

import threading
import time

try:
    import serial
except ImportError:
    serial = None

# MANUEL fallback sabitleri (GPS fix yoksa kullanilir) — Elazig ili, yaklasik.
ELAZIG_LAT = 38.6810
ELAZIG_LON = 39.2264
ELAZIG_ALT = 950.0


def _nmea_to_decimal(value: str, hemisphere: str) -> float:
    """NMEA ddmm.mmmm / dddmm.mmmm formatini ondalik dereceye cevirir."""
    raw = float(value)
    degrees = int(raw / 100)
    minutes = raw - degrees * 100
    decimal = degrees + minutes / 60.0
    if hemisphere in ("S", "W"):
        decimal = -decimal
    return decimal


class GPSReader:
    """
    Verilen COM portundan NMEA verisi okuyan arka plan thread'i.

    Kullanim:
        reader = GPSReader(port="COM5")
        reader.start()
        ...
        pos = reader.get_position()   # {"lat":.., "lon":.., "alt":.., "source":.., "fix": bool}
        ...
        reader.stop()
    """

    def __init__(self, port: str, baudrate: int = 9600, timeout: float = 1.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout

        self._lock = threading.Lock()
        self._fix = False
        self._lat = ELAZIG_LAT
        self._lon = ELAZIG_LON
        self._alt = ELAZIG_ALT

        self._serial = None
        self._thread = None
        self._stop_event = threading.Event()

    def start(self):
        """Arka plan okuma thread'ini baslatir. Port acilamazsa MANUEL modda kalir."""
        if serial is None:
            return
        if self._thread is not None and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        """Okuma thread'ini ve seri portu duzgunce kapatir."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        if self._serial is not None:
            try:
                self._serial.close()
            except Exception:
                pass
            self._serial = None

    def get_position(self) -> dict:
        """Son bilinen konumu dondurur; fix yoksa MANUEL (Elazig) konumunu dondurur."""
        with self._lock:
            if self._fix:
                return {"lat": self._lat, "lon": self._lon, "alt": self._alt,
                        "source": "GPS_FIX", "fix": True}
            return {"lat": ELAZIG_LAT, "lon": ELAZIG_LON, "alt": ELAZIG_ALT,
                    "source": "MANUEL", "fix": False}

    def _run(self):
        try:
            self._serial = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
        except Exception:
            self._serial = None
            return

        while not self._stop_event.is_set():
            try:
                raw = self._serial.readline()
            except Exception:
                break

            try:
                line = raw.decode("ascii", errors="ignore").strip()
            except Exception:
                continue

            if line.startswith("$GPGGA") or line.startswith("$GNGGA"):
                self._parse_gga(line)

    def _parse_gga(self, line: str):
        fields = line.split(",")
        if len(fields) < 10:
            return

        try:
            fix_quality = int(fields[6]) if fields[6] else 0
        except ValueError:
            fix_quality = 0

        if fix_quality <= 0:
            with self._lock:
                self._fix = False
            return

        try:
            lat = _nmea_to_decimal(fields[2], fields[3])
            lon = _nmea_to_decimal(fields[4], fields[5])
            alt = float(fields[9]) if fields[9] else ELAZIG_ALT
        except (ValueError, IndexError):
            with self._lock:
                self._fix = False
            return

        with self._lock:
            self._fix = True
            self._lat = lat
            self._lon = lon
            self._alt = alt

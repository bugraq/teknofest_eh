"""
Bagimsiz tani (diagnostic) scripti: COM9'dan gelen HAM seri veriyi, hicbir
NMEA parse/filtreleme yapmadan oldugu gibi ekrana basar.

GPSReader sinifini KULLANMAZ, dogrudan pyserial ile calisir. Amac: COM9'dan
gercekten veri gelip gelmedigini, geliyorsa formatinin ne oldugunu gormek.

Calistirma:
    .venv\\Scripts\\python.exe gps_raw_test.py
"""

import time

try:
    import serial
except ImportError as e:
    print(f"pyserial kurulu degil (hata yakalandi, cokme yok): {e}")
    raise SystemExit(0)

PORT = "COM9"
BAUDRATE = 9600
TIMEOUT = 1
TOTAL_SECONDS = 90


def main():
    print(f"COM9 aciliyor: port={PORT}, baudrate={BAUDRATE}, timeout={TIMEOUT}")

    try:
        ser = serial.Serial(PORT, BAUDRATE, timeout=TIMEOUT)
    except Exception as e:
        print(f"Port acilamadi (hata yakalandi, cokme yok): {e}")
        return

    line_count = 0
    start = time.time()

    try:
        while time.time() - start < TOTAL_SECONDS:
            try:
                raw = ser.readline()
            except Exception as e:
                print(f"readline() hatasi (yakalandi): {e}")
                break

            if not raw:
                continue

            try:
                line = raw.decode("ascii", errors="ignore").strip()
            except Exception as e:
                print(f"decode hatasi (yakalandi): {e}")
                continue

            if line:
                line_count += 1
                print(f"[{line_count}] {line}")
    except Exception as e:
        print(f"Beklenmeyen hata (yakalandi, cokme yok): {e}")
    finally:
        try:
            ser.close()
        except Exception:
            pass

    if line_count == 0:
        print("Hic veri alinamadi.")
    else:
        print(f"\nToplam {line_count} satir alindi.")


if __name__ == "__main__":
    main()

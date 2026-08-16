"""
Bagimsiz test scripti: hardware/gps_reader.py'deki GPSReader'i gercek
donanimla (COM9 uzerindeki u-blox GPS/GNSS alicisi) test eder.

Bu script hicbir proje dosyasina (state_manager.py, panel_map.py,
main_window.py) bagli degildir, sadece GPSReader'i kullanir.

Calistirma:
    .venv\\Scripts\\python.exe gps_live_test.py
"""

import time

from hardware.gps_reader import GPSReader

PORT = "COM9"
BAUDRATE = 9600
TOTAL_SECONDS = 15
PRINT_INTERVAL = 2


def main():
    print(f"GPSReader baslatiliyor: port={PORT}, baudrate={BAUDRATE}")

    try:
        reader = GPSReader(port=PORT, baudrate=BAUDRATE)
        reader.start()
    except Exception as e:
        print(f"GPSReader baslatilamadi (hata yakalandi, cokme yok): {e}")
        return

    elapsed = 0
    try:
        while elapsed < TOTAL_SECONDS:
            time.sleep(PRINT_INTERVAL)
            elapsed += PRINT_INTERVAL
            try:
                pos = reader.get_position()
                print(
                    f"[{elapsed:>2}s] lat={pos['lat']:.6f}  lon={pos['lon']:.6f}  "
                    f"alt={pos['alt']:.1f}  source={pos['source']}  fix={pos['fix']}"
                )
            except Exception as e:
                print(f"[{elapsed:>2}s] get_position() hatasi (yakalandi): {e}")
    except Exception as e:
        print(f"Beklenmeyen hata (yakalandi, cokme yok): {e}")
    finally:
        try:
            reader.stop()
            print("GPSReader durduruldu.")
        except Exception as e:
            print(f"stop() sirasinda hata (yakalandi): {e}")


if __name__ == "__main__":
    main()

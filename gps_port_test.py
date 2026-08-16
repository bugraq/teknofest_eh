"""
Bagimsiz test scripti: bilgisayarda mevcut COM portlarini listeler.
Bu script hicbir proje dosyasina bagli degildir, sadece pyserial kullanir.

Calistirma:
    .venv\\Scripts\\python.exe gps_port_test.py
"""

import serial.tools.list_ports as list_ports


def main():
    ports = list(list_ports.comports())

    if not ports:
        print("Hicbir COM portu bulunamadi.")
        return

    print(f"{len(ports)} adet COM portu bulundu:\n")
    for p in ports:
        print(f"Port         : {p.device}")
        print(f"Aciklama     : {p.description}")
        print(f"Uretici (HWID): {p.hwid}")
        print(f"Manufacturer : {p.manufacturer}")
        print(f"VID:PID      : {p.vid}:{p.pid}" if p.vid else "VID:PID      : (yok)")
        print(f"Seri No      : {p.serial_number}")
        print("-" * 40)


if __name__ == "__main__":
    main()

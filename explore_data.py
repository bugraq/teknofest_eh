import h5py
import matplotlib.pyplot as plt
import numpy as np

# Dosya yolumuzu veriyoruz (Seninkini direkt yazdım)
dosya_yolu = r"C:\Users\obugr\OneDrive\Masaüstü\BPSK-20.h5"

print("--- VERİ SETİNİN İÇİNE GİRİLİYOR ---")

with h5py.File(dosya_yolu, 'r') as f:
    # İlgili sütunları (Key'leri) hafızaya alıyoruz
    iq_data = f['dataset']
    mod_labels = f['labels_mod']
    snr_labels = f['labels_snr']
    cfo_labels = f['labels_cfo']
    
    # Kanka burası çok önemli: Hangi sıradaki veriye bakmak istiyorsun? 
    # 0'dan 9999'a kadar bir sayı seçebilirsin. Biz ilk veriye (0. index) bakalım.
    ornek_index = 0
    
    # 1. ETİKETLERİ (SAYILARI) OKUYALIM
    # Not: Etiketler (1, 10000) formatında olduğu için [0, ornek_index] şeklinde okuyoruz
    mod_kodu = mod_labels[0, ornek_index]
    snr_degeri = snr_labels[0, ornek_index]
    cfo_degeri = cfo_labels[0, ornek_index]
    
    print(f"\n[{ornek_index}. Verinin Etiketleri]")
    print(f"Modülasyon Kodu : {mod_kodu} (Muhtemelen BPSK)")
    print(f"SNR Seviyesi    : {snr_degeri} dB")
    print(f"CFO (Frekans Kayması): {cfo_degeri:.2f} Hz")
    
    # 2. HAM SİNYALİ (IQ) OKUYALIM
    # Veri (2, 1024) formatında. 0. satır I (Reel), 1. satır Q (Sanal) kanalı
    sinyal = iq_data[ornek_index]
    I_kanali = sinyal[0] # İlk 1024'lük dizi
    Q_kanali = sinyal[1] # İkinci 1024'lük dizi
    
    print("\n[Ham IQ Verisi (İlk 5 Değer)]")
    print(f"I Kanalı: {I_kanali[:5]}")
    print(f"Q Kanalı: {Q_kanali[:5]}")

    # 3. VERİYİ GÖZÜMÜZLE GÖRMEK İÇİN ÇİZDİRELİM
    plt.figure(figsize=(12, 5))
    plt.style.use('dark_background') # Havalı dursun
    
    # Sinyalin tamamı (1024) çok sıkışık görünür, o yüzden ilk 200 örneği çizdiriyoruz
    gosterilecek_uzunluk = 200 
    
    plt.plot(I_kanali[:gosterilecek_uzunluk], label='I Kanalı (Reel)', color='lime', linewidth=1.5)
    plt.plot(Q_kanali[:gosterilecek_uzunluk], label='Q Kanalı (Sanal)', color='cyan', linewidth=1.5, alpha=0.8)
    
    plt.title(f"Sinyal Grafiği - Index: {ornek_index} | SNR: {snr_degeri}dB")
    plt.xlabel("Zaman (Sample)")
    plt.ylabel("Genlik")
    plt.grid(color='gray', linestyle='--', alpha=0.3)
    plt.legend()
    plt.show()
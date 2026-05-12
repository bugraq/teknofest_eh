import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import QVBoxLayout, QWidget


class WaterfallAndIQPlot(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0) # Kenar boşluklarını sıfırla

        # PyQtGraph'ın ana çizim tahtasını oluştur
        self.graphics_layout = pg.GraphicsLayoutWidget()
        self.graphics_layout.setBackground('#1e293b') # Arka plan Slate Dark uyumlu
        self.layout.addWidget(self.graphics_layout)

        # ---------------------------------------------------
        # 1. ÜST GRAFİK: Ham IQ Sinyali (Zaman Serisi)
        # ---------------------------------------------------
        self.iq_plot = self.graphics_layout.addPlot(title="Canlı IQ Sinyali (I-Kanalı)")
        self.iq_plot.setYRange(-3, 3) # Genlik sınırları
        self.iq_plot.showGrid(x=True, y=True, alpha=0.3)
        # Modern mavi kalemimiz
        self.iq_curve = self.iq_plot.plot(pen=pg.mkPen(color='#3b82f6', width=1.5))

        self.graphics_layout.nextRow() # Alt satıra geç

        # ---------------------------------------------------
        # 2. ALT GRAFİK: Şelale (Waterfall) Spektrumu
        # ---------------------------------------------------
        self.waterfall_plot = self.graphics_layout.addPlot(title="Frekans Şelalesi (Waterfall)")
        self.waterfall_plot.setLabel('bottom', 'Frekans (Bant)')
        self.waterfall_plot.setLabel('left', 'Zaman')
        
        # Waterfall bir resim (ImageItem) olarak çizilir, çok daha hızlıdır
        self.waterfall_image = pg.ImageItem()
        self.waterfall_plot.addItem(self.waterfall_image)

        # Renk Haritası (Cyberpunk / Radar Teması: Lacivertten Yeşile ve Sarıya)
        colormap = pg.colormap.get('viridis') 
        self.waterfall_image.setColorMap(colormap)

        # Şelale Hafızası: 100 satır geçmiş, 512 sütun frekans çözünürlüğü
        self.history_size = 100
        self.fft_size = 512
        # Başlangıçta simsiyah bir matris
        self.waterfall_data = np.zeros((self.history_size, self.fft_size))

    def update_plots(self, iq_data, fft_data):
        """ Bu fonksiyon dışarıdan gelen canlı veriyle grafikleri günceller """
        # 1. IQ Eğrisini Güncelle
        self.iq_curve.setData(iq_data)

        # 2. Şelaleyi Güncelle (Matrisi bir satır aşağı kaydır, en üste yeni FFT'yi koy)
        self.waterfall_data = np.roll(self.waterfall_data, -1, axis=0)
        self.waterfall_data[-1, :] = fft_data
        
        # Resmi ekrana bas (autoLevels=False yaparak performansı artırıyoruz)
        self.waterfall_image.setImage(self.waterfall_data, autoLevels=False, levels=(0, 10))
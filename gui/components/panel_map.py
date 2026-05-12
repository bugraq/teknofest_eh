from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel

# QWebEngineView ve Folium modüllerini güvenli bir şekilde import etmeyi deniyoruz
try:
    import requests
    import folium
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    HAS_MAP_MODULES = True
except ImportError:
    HAS_MAP_MODULES = False

class SignalMapPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Başlık
        self.title_lbl = QLabel("TAKTİK SİNYAL KONUM HARİTASI (GERÇEK ZAMANLI)")
        self.title_lbl.setStyleSheet("color: #94a3b8; font-size: 13px; font-weight: bold; background: transparent; padding: 5px;")
        self.layout.addWidget(self.title_lbl)

        self.has_map_modules = HAS_MAP_MODULES

        if self.has_map_modules:
            self.web_view = QWebEngineView()
            # Arka plan rengini Slate Dark'a uyumlu yapalım ki yüklenirken beyaz patlamasın
            self.web_view.setStyleSheet("background-color: #1e293b;") 
            self.layout.addWidget(self.web_view)
            self.init_real_map()
        else:
            self.err_lbl = QLabel("Harita Modülü Devre Dışı.\n\nHaritayı görmek için terminalden indirmeyi tamamlayın:\npip install PyQt6-WebEngine folium")
            self.err_lbl.setStyleSheet("color: #94a3b8; font-size: 14px; font-weight: bold; padding: 20px; background-color: #1e293b; border-radius: 8px;")
            self.layout.addWidget(self.err_lbl)
            self.layout.addStretch()

        self.target_coords = []
        self.map_obj = None

    def init_real_map(self):
        """ Konumu bulur ve folium ile haritayı çizer """
        if not getattr(self, 'has_map_modules', False):
            return

        import requests
        import folium

        # Varsayılan değer (Hata olursa Ankara'da kalır)
        self.current_lat = 39.9208
        self.current_lon = 32.8541
        
        # IP tabanlı konum (Bilgisayarın bağlı olduğu Wi-Fi/ISS üzerinden şehri bulur)
        try:
            res = requests.get('http://ip-api.com/json/', timeout=3).json()
            if res['status'] == 'success':
                self.current_lat = res['lat']
                self.current_lon = res['lon']
        except Exception:
            pass

        # Folium haritası oluştur (CartoDB dark_matter = Modern Karanlık Tema)
        self.map_obj = folium.Map(
            location=[self.current_lat, self.current_lon], 
            zoom_start=11, 
            tiles='CartoDB dark_matter',
            control_scale=True
        )

        # Kendi konumumuza MAVİ renkli bir hedef işaretçisi koy
        folium.Marker(
            [self.current_lat, self.current_lon], 
            popup='SDR Komuta Merkezi (Anlık Konumunuz)', 
            icon=folium.Icon(color='blue', icon='info-sign')
        ).add_to(self.map_obj)
        
        # Haritayı raw HTML string olarak al ve QWebEngineView içerisine renderla
        html_content = self.map_obj.get_root().render()
        self.web_view.setHtml(html_content)

    def add_target(self, x, y):
        """ 
        Gerçek haritada yön bulma (DF) ve mesafe verisiyle JS interop kullanılarak 
        dinamik hedef (marker) ekliyoruz. x ve y değerleri kilometre cinsinden ofsettir.
        """
        if not getattr(self, 'has_map_modules', False) or self.map_obj is None:
            return
            
        import math
        
        # x ve y kilometre ofsetlerini yaklaşık enlem/boylam ofsetine çevir
        delta_lat = y / 111.0
        delta_lon = x / (111.0 * math.cos(math.radians(self.current_lat)))
        
        target_lat = self.current_lat + delta_lat
        target_lon = self.current_lon + delta_lon
        
        distance = math.sqrt(x**2 + y**2)
        
        # Folium haritasının JS tarafındaki değişken adını alıyoruz (Örn: map_8a1792...)
        map_name = self.map_obj.get_name()
        
        # Leaflet JS kütüphanesini kullanarak canlı haritaya marker ekleyen kod
        js_code = f"""
        (function() {{
            if (typeof {map_name} !== 'undefined') {{
                // Kırmızı bir tespit çemberi ekle
                var circle = L.circleMarker([{target_lat}, {target_lon}], {{
                    color: '#ef4444',
                    fillColor: '#ef4444',
                    fillOpacity: 0.8,
                    radius: 7
                }}).addTo({map_name});
                
                circle.bindPopup("<b>Tespit Edilen Sinyal</b><br>Mesafe: {distance:.2f} km").openPopup();
                
                // Harita çok dolmasın diye 4 saniye sonra sinyali sil
                setTimeout(function() {{
                    {map_name}.removeLayer(circle);
                }}, 4000);
            }}
        }})();
        """
        self.web_view.page().runJavaScript(js_code)
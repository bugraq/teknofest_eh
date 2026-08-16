import json
import math

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel

try:
    import config
except ImportError:
    from ... import config

# QWebEngineView ve Folium modüllerini güvenli bir şekilde import etmeyi deniyoruz
try:
    import folium
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    HAS_MAP_MODULES = True
except ImportError:
    HAS_MAP_MODULES = False

class SignalMapPanel(QWidget):
    def __init__(self, state_manager=None):
        super().__init__()
        self.state_manager = state_manager
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Başlık
        self.title_lbl = QLabel("TAKTİK SİNYAL KONUM HARİTASI (GERÇEK ZAMANLI)")
        self.title_lbl.setStyleSheet("color: #94a3b8; font-size: 13px; font-weight: bold; background: transparent; padding: 5px;")
        self.layout.addWidget(self.title_lbl)

        self.has_map_modules = HAS_MAP_MODULES

        # DİKKAT: Bunlar init_real_map()'ten ÖNCE kurulmalı. Eskiden sonra
        # geliyordu ve haritayı kurduktan sonra map_obj'i None'a çekiyordu —
        # bu yüzden add_target() her çağrıda sessizce geri dönüyor, haritaya
        # hiçbir hedef düşmüyordu.
        self.target_coords = []
        self.map_obj = None

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

    def init_real_map(self):
        """ Konumu bulur ve folium ile haritayı çizer """
        if not getattr(self, 'has_map_modules', False):
            return

        import folium

        # Kendi konumumuz: GPS alıcı fix verdiyse state_manager'dan, yoksa
        # config.HOME_* (Elazığ).
        #
        # NOT: Burada eskiden IP tabanlı konum (ip-api.com) kullanılıyordu.
        # Kaldırıldı: sahada internet olmayabilir, olsa bile IP geolocation
        # operatörün şehir merkezini verir — antenin yerini değil. Hedef
        # hesapları kendi konumumuza dayandığı için bu hata her şeye yayılırdı.
        self.current_lat = config.HOME_LAT
        self.current_lon = config.HOME_LON
        if self.state_manager is not None:
            try:
                st = self.state_manager.get_state()
                if st.get("has_gps_fix"):
                    self.current_lat = st["own_lat"]
                    self.current_lon = st["own_lon"]
            except Exception:
                pass

        # Folium haritası oluştur (CartoDB dark_matter = Modern Karanlık Tema)
        # zoom_start=17 ≈ 1 km²'lik alan. Şehir ölçeğinde (zoom 11) konum
        # hatası birkaç piksel kalıyor ve hedefin kaydığı görülmüyordu.
        self.map_obj = folium.Map(
            location=[self.current_lat, self.current_lon],
            zoom_start=17,
            tiles='CartoDB dark_matter',
            control_scale=True
        )

        # 1 km²'lik operasyon alanını çiz (config.MAP_AREA_SIZE_M)
        half_deg_lat = (config.MAP_AREA_SIZE_M / 2.0) / 111_320.0
        half_deg_lon = half_deg_lat / max(math.cos(math.radians(self.current_lat)), 1e-6)
        folium.Rectangle(
            bounds=[
                [self.current_lat - half_deg_lat, self.current_lon - half_deg_lon],
                [self.current_lat + half_deg_lat, self.current_lon + half_deg_lon],
            ],
            color="#10b981", weight=2, fill=False, dash_array="6",
            popup=f"Operasyon Alanı ({config.MAP_AREA_SIZE_M:.0f} m × "
                  f"{config.MAP_AREA_SIZE_M:.0f} m)",
        ).add_to(self.map_obj)

        # Kendi konumumuza MAVİ renkli bir hedef işaretçisi koy
        folium.Marker(
            [self.current_lat, self.current_lon], 
            popup='SDR Komuta Merkezi (Anlık Konumunuz)', 
            icon=folium.Icon(color='blue', icon='info-sign')
        ).add_to(self.map_obj)
        
        # Haritayı raw HTML string olarak al ve QWebEngineView içerisine renderla
        html_content = self.map_obj.get_root().render()
        self.web_view.setHtml(html_content)

    def set_target_latlon(self, lat, lon, err_m=0.0, label="Tespit Edilen Sinyal"):
        """
        Hedefi MUTLAK koordinatla işaretler (TDoA/AOA çözücüsünün çıktısı).

        err_m verilirse hedefin etrafına o yarıçapta belirsizlik dairesi çizilir —
        nokta tek başına "tam burada" izlenimi verir, oysa çözümün bir hatası var.
        """
        if not getattr(self, 'has_map_modules', False) or self.map_obj is None:
            return
        self._draw_target(lat, lon, err_m=err_m, label=label)

    def add_target(self, x, y):
        """
        Gerçek haritada yön bulma (DF) ve mesafe verisiyle JS interop kullanılarak
        dinamik hedef (marker) ekliyoruz. x ve y değerleri kilometre cinsinden ofsettir.
        """
        if not getattr(self, 'has_map_modules', False) or self.map_obj is None:
            return

        # x ve y kilometre ofsetlerini yaklaşık enlem/boylam ofsetine çevir
        delta_lat = y / 111.0
        delta_lon = x / (111.0 * math.cos(math.radians(self.current_lat)))

        target_lat = self.current_lat + delta_lat
        target_lon = self.current_lon + delta_lon

        distance = math.sqrt(x**2 + y**2)
        self._draw_target(target_lat, target_lon, distance_km=distance)

    def _draw_target(self, target_lat, target_lon, err_m=0.0,
                     distance_km=None, label="Tespit Edilen Sinyal"):
        """Haritaya geçici hedef işareti + belirsizlik dairesi basar."""
        if distance_km is None:
            dlat = (target_lat - self.current_lat) * 111.0
            dlon = ((target_lon - self.current_lon) * 111.0
                    * math.cos(math.radians(self.current_lat)))
            distance = math.sqrt(dlat ** 2 + dlon ** 2)
        else:
            distance = distance_km

        # Folium haritasının JS tarafındaki değişken adını alıyoruz (Örn: map_8a1792...)
        map_name = self.map_obj.get_name()
        
        # Leaflet JS kütüphanesini kullanarak canlı haritaya marker ekleyen kod
        # Belirsizlik dairesi: hedef noktanın tek başına gösterilmesi "tam olarak
        # burada" izlenimi verir. err_m verilmişse gerçek hata payı da çizilir.
        err_js = ""
        if err_m and err_m > 0:
            err_js = f"""
                var err = L.circle([{target_lat}, {target_lon}], {{
                    radius: {err_m},
                    color: '#f59e0b', weight: 1, dashArray: '4',
                    fillColor: '#f59e0b', fillOpacity: 0.12
                }}).addTo({map_name});
                setTimeout(function() {{ {map_name}.removeLayer(err); }}, 4000);
            """

        js_code = f"""
        (function() {{
            if (typeof {map_name} !== 'undefined') {{
                {err_js}
                // Kırmızı bir tespit çemberi ekle
                var circle = L.circleMarker([{target_lat}, {target_lon}], {{
                    color: '#ef4444',
                    fillColor: '#ef4444',
                    fillOpacity: 0.8,
                    radius: 7
                }}).addTo({map_name});

                circle.bindPopup("<b>{label}</b><br>Mesafe: {distance:.2f} km").openPopup();

                // Harita çok dolmasın diye 4 saniye sonra sinyali sil
                setTimeout(function() {{
                    {map_name}.removeLayer(circle);
                }}, 4000);
            }}
        }})();
        """
        self.web_view.page().runJavaScript(js_code)

    # ── KONUM BULMA (Ana Ekran'daki Yön Bulma paneli tetikler) ──────────────
    def start_location_finding(self, real_lat, real_lon):
        """
        GERÇEK konumu sabit mavi marker olarak çizer ve haritayı geri çekip
        (~10-15 km yarıçaplı SAHTE sıçramaları görebilecek şekilde) ortalar.

        SAHTE bölge burada ÇİZİLMEZ — ilk konumu da update_fake_area() ile
        gelir (main_window ilk tick'i start ile aynı anda tetikler).
        """
        if not getattr(self, "has_map_modules", False) or self.map_obj is None:
            return
        map_name = self.map_obj.get_name()
        label = json.dumps(f"GERÇEK ({real_lat:.4f}°N, {real_lon:.4f}°E)")
        js = f"""
        (function() {{
            if (typeof {map_name} === 'undefined') return;
            {map_name}.setView([{real_lat}, {real_lon}], 11);
            if (window.__lfRealMarker) {{ {map_name}.removeLayer(window.__lfRealMarker); }}
            window.__lfRealMarker = L.circleMarker([{real_lat}, {real_lon}], {{
                radius: 9, color: '#93c5fd', weight: 2,
                fillColor: '#3b82f6', fillOpacity: 0.95
            }}).addTo({map_name});
            window.__lfRealMarker.bindTooltip({label}, {{
                permanent: true, direction: 'right', offset: [10, 0]
            }}).openTooltip();
        }})();
        """
        self.web_view.page().runJavaScript(js)

    def update_fake_area(self, fake_lat, fake_lon, radius_m=1500):
        """
        SAHTE bölgeyi (yarı saydam turuncu/kırmızı daire — KESİN NOKTA değil,
        belirsizlik alanı) günceller; yoksa oluşturur. Etiket sadece "SAHTE" —
        koordinat yazmaz.
        """
        if not getattr(self, "has_map_modules", False) or self.map_obj is None:
            return
        map_name = self.map_obj.get_name()
        js = f"""
        (function() {{
            if (typeof {map_name} === 'undefined') return;
            if (window.__lfFakeCircle) {{
                window.__lfFakeCircle.setLatLng([{fake_lat}, {fake_lon}]);
            }} else {{
                window.__lfFakeCircle = L.circle([{fake_lat}, {fake_lon}], {{
                    radius: {radius_m}, color: '#ef4444', weight: 2,
                    fillColor: '#f97316', fillOpacity: 0.35
                }}).addTo({map_name});
                window.__lfFakeCircle.bindTooltip('SAHTE', {{
                    permanent: true, direction: 'top'
                }}).openTooltip();
            }}
        }})();
        """
        self.web_view.page().runJavaScript(js)

    def stop_location_finding(self):
        """KONUM BULMA modu durdurulunca GERÇEK/SAHTE katmanlarını temizler."""
        if not getattr(self, "has_map_modules", False) or self.map_obj is None:
            return
        map_name = self.map_obj.get_name()
        js = f"""
        (function() {{
            if (typeof {map_name} === 'undefined') return;
            if (window.__lfRealMarker) {{
                {map_name}.removeLayer(window.__lfRealMarker); window.__lfRealMarker = null;
            }}
            if (window.__lfFakeCircle) {{
                {map_name}.removeLayer(window.__lfFakeCircle); window.__lfFakeCircle = null;
            }}
        }})();
        """
        self.web_view.page().runJavaScript(js)
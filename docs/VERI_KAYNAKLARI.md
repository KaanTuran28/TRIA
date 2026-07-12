# TRIA — Profesyonel & Yasal Veri Edinim Rehberi (Türkiye)

Son güncelleme: 2026-07-12 · Bu belge, TRIA C4I'ın veri beslemelerini **yasal, sürdürülebilir ve
profesyonel** hale getirmek için kaynak envanteri ve entegrasyon planıdır.

## 0. İBB Trafik Duyuru Verisi — Güncellik Doğrulaması (2026-07-12)

`resource_id=1c043914-8a76-4793-bae9-c60a68c7d389` hâlâ portaldaki **tek ve güncel** trafik
duyuru kaynağı — farklı/yeni bir resource_id bulunamadı. Ancak canlı sorguda (`sort=_id desc`)
en yeni kaydın **2025-03-05** tarihli olduğu gözlendi (148.194 kayıt) — yani veri seti o
tarihten beri görünürde beslenmiyor. Bu, İBB tarafında geçici bir senkronizasyon sorunu veya
kalıcı bir durum olabilir; ingestor kodu (`app/scrapers/ibb_ingestor.py`) değişiklik gerektirmez,
sadece periyodik olarak (`GET /ingest/ibb/metrics`) en son kaydın tarihi kontrol edilmeli.
Ayrıca portalda **"Trafik Yoğunluk Haritası"** (`traffic-density-map`) adlı ayrı bir veri seti
bulundu — bu olay-düzeyi değil, **anlık yoğunluk/hız** verisi sunar (farklı şema); ileride
"canlı trafik yoğunluğu" katmanı için ayrı bir ingestor konusu olabilir, dispatch/incident
akışına doğrudan uymuyor.

## 1. Resmi / Açık Veri Kaynakları (öncelikli)

| Kaynak | URL | Veri | Erişim | Entegrasyon durumu |
|---|---|---|---|---|
| **İBB Açık Veri Portalı** | data.ibb.gov.tr | Trafik duyuruları (tip + lat/lon + tarih), UKOME, kamera konumları | **CKAN Datastore API** (JSON, ücretsiz) | `sources.json > official_apis.ibb_trafik_duyuru` — ingestor yazılacak (İş #1) |
| **TÜİK Veri Portalı** | data.tuik.gov.tr | Güvenlik/adalet istatistikleri, il bazlı yıllık | Excel/CSV toplu indirme | Trend doğrulama + nüfusa oranlama için planlandı |
| **Adalet Bakanlığı (Adli Sicil ve İstatistik GM)** | adlisicil.adalet.gov.tr | UYAP kaynaklı adli istatistik yıllıkları | PDF/Excel | Doğrulama katmanı |
| **Resmi İstatistik Portalı** | resmiistatistik.gov.tr | Suç, adalet ve seçim istatistikleri konu başlığı | Portal | Referans |
| **ULAŞAV (Çevre ve Şehircilik Bak.)** | ulasav.csb.gov.tr | Ulusal akıllı şehir açık veri | Portal/API | Şehir bazlı ek katmanlar |
| **İçişleri Bakanlığı — İller İdaresi** | icisleri.gov.tr | İstatistikî bilgiler | Sayfa/PDF | Referans |

**Neden İBB trafik verisi ilk sırada:** Gerçek zamanlıya yakın, koordinatlı (lat/lon), resmi ve açık
lisanslı tek olay-düzeyi beslemedir → `traffic_accident` incident_type'ını doğrudan doldurur.

## 2. Mevcut OSINT Beslemeleri (çalışıyor)

- **Kurumsal RSS:** AA, NTV, Hürriyet, Habertürk vb. (`sources.json > rss`) — kamuya açık RSS tüketimi yasaldır; içerik tam metin kopyalanmaz, başlık+özet işlenir, `source_url` ile kaynağa atıf verilir.
- **GDELT GKG v1:** Küresel akademik açık veri — Türkiye filtrelenmiş sorgular.
- **Google News RSS / Reddit RSS / Telegram t.me/s önizleme:** Kamuya açık uçlar; oran sınırlaması ve `robots.txt` gözetilir.

## 3. Hukuki Çerçeve (uyum kuralları)

1. **KVKK (6698):** Olay kayıtlarında kişisel veri tutulmaz. LLM system prompt'u isim/plaka/TC
   üretmeyi açıkça yasaklar (`groq_analyzer.SYSTEM_PROMPT`). Konum, il/ilçe merkez çözünürlüğündedir
   (adres düzeyi hassasiyet saklanmaz).
2. **Telif:** Haber tam metni arşivlenmez; `raw_news_archive` yalnızca URL + başlık + hash tutar.
   Türetilmiş veri (kategori, şiddet skoru, koordinat) özgün analizdir.
3. **Açık veri lisansları:** İBB/TÜİK açık veri lisansları atıf ister — rapor ve UI'da kaynak alanı
   zaten gösteriliyor.
4. **Oran sınırlama:** Scraper 60 dk periyot + `LLM_COOLDOWN_SECONDS`; resmi API'lerde belgelenen
   limitlere uyulur.
5. **Kapsam dışı:** 155/112 çağrı verisi gibi kapalı kamu verileri ancak resmi protokol/izinle
   kullanılabilir — üniversite bitirme projesi kapsamında talep yazısı örneği hazırlanabilir.

## 4. Entegrasyon Planı (sıralı)

1. ✅ **İBB CKAN ingestor** — `app/scrapers/ibb_ingestor.py`, canlı doğrulandı (2026-07-12).
2. ✅ **TÜİK nüfus normalizasyonu** — `app/modules/crime/population.py` (ADNKS 2025, 81 il),
   `/analytics/trends` ve `/analytics/corridors` çıktısında `per_100k` alanı.
3. ✅ **İl bazlı choropleth sınırları** — `frontend/static/geo/turkey-il.geojson` (OSM tabanlı,
   81 il, sadeleştirilmiş ~225 KB), kaynak: `izzetkalic/geojsons-of-turkey` (ODbL, OpenStreetMap
   katkıda bulunanları). Frontend'de `/analytics/trends` ile il adına göre client-side birleştirilir.
4. [ ] **AFAD/Kandilli** (opsiyonel): fire_anomaly bağlamında yangın/patlama teyidi (deprem hariç).
5. [ ] **İBB Trafik Yoğunluk Haritası**: farklı şema (yoğunluk/hız, olay değil) — ayrı bir
   "canlı trafik" katmanı olarak değerlendirilebilir, dispatch akışına dahil edilmez.

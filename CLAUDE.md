# TRIA C4I — Gerçek Zamanlı Kolluk İstihbarat Ağı

> **Proje durumu (son güncelleme: 2026-07-13, v2.4):** Performans KPI'ları (sevk gecikmesi /
> seyahat / sahne süresi / toplam müdahale) ve kapsama boşluğu analizi (risk yüksek ama
> devriyeye uzak bölgeler) eklendi — C4I sisteminin somut değerini ölçülebilir kılan iki
> özellik. **65 test** geçiyor, Docker'da canlı veriyle uçtan uca doğrulandı.

## Tarayıcı Doğrulaması (2026-07-12/13, Playwright)

Backend'i curl ile değil, gerçek headless Chromium ile sürüp ekran görüntüsü + konsol +
WebSocket + piksel-fark analiziyle doğruladım. Bulgular:

- ✅ Choropleth: 81 poligon render oluyor, devriye ikonları gerçekten hareket ediyor
  (piksel-fark testiyle kanıtlandı — `EKIP-34-02` mavi→kırmızı durum geçişi görsel olarak yakalandı),
  WebSocket 3 sn'de bir canlı frame akıtıyor, konsol hatası yok.
- 🐛 **Düzeltildi:** Admin panelde İBB butonu hata verdiğinde (`401` vb.) hata mesajı `runIbbIngest()`
  içinde hemen ardından çağrılan `refreshAll()` tarafından anında eziliyordu — kullanıcı hatayı
  hiç göremiyordu. `runScrape()`'teki mevcut `setTimeout(refreshAll, 6000)` deseni uygulandı.
- 🐛 **Düzeltildi:** Admin paneli başlığı/title'ı hâlâ pre-C4I metnini gösteriyordu
  ("OSINT veri işleme ve CBS haritalama — makale kanıt sistemi"). "TRIA C4I — Yönetim Paneli"
  olarak güncellendi (`app/ui/admin.py`).
- 📌 **Bug değil, davranış notu:** Harita "0 görünür" gösterebilir çünkü `/geojson` varsayılan
  90 günlük pencere kullanıyor (v2.1 performans kararı) ve İBB veri seti 2025-03 tarihli
  (pencerenin dışında). Demo için `POST /scrape` ile taze OSINT verisi çekilmeli, ya da
  `/geojson?days=600` gibi genişletilmiş pencere kullanılmalı.

## Mimari Özet

- **Backend:** FastAPI (async) + SQLAlchemy 2 (asyncpg) + PostgreSQL/PostGIS + APScheduler + Alembic
- **Veri besleyiciler (DOKUNMA — çalışıyor):** RSS/GDELT/Telegram OSINT scraper (`app/modules/crime/scraper.py`) + Groq LLM analiz (`app/services/groq_analyzer.py`) + İBB resmi trafik ingestor (`app/scrapers/ibb_ingestor.py`)
- **Frontend:** Leaflet.js (vanilla JS), dark tema, `frontend/` altında

## Modül Haritası

| Yol | Görev |
|---|---|
| `app/modules/crime/` | OSINT olay hattı: scraper → Groq parse → geolocation → `crime_events` |
| `app/modules/crime/population.py` | TÜİK ADNKS 2025 il nüfusları (81 il), `per_100k()` normalizasyon |
| `app/modules/c4i/models.py` | `police_units`, `police_unit_history` (iz sürme) |
| `app/modules/c4i/simulation.py` | 3 sn tick: patrol/dispatch/onscene 3 modlu hareket motoru + 60 sn'de bir geçmiş snapshot |
| `app/modules/c4i/dispatch.py` | Öncelik kuyruğu (şiddet + bekleme bonusu), haversine, ETA, DB-tabanlı atama (`assigned_unit_id`/`resolved_at`) |
| `app/modules/c4i/predictive.py` | Kural-tabanlı erken uyarı skoru (bkz. Prediktif Risk bölümü) |
| `app/modules/c4i/performance.py` | Sevk gecikmesi/seyahat/sahne/toplam müdahale süresi KPI'ları (saf fonksiyonlar) |
| `app/modules/c4i/coverage.py` | Kapsama boşluğu skoru (en yakın birime mesafe × şiddet × olay sayısı) |
| `app/modules/c4i/router.py` | `/units`, `/ws/units`, `/units/{id}/history`, `/analytics/*`, `/incidents/queue`, `/incidents/{id}/resolve` |
| `app/modules/crime/spatial.py` | PostGIS çokgen/yarıçap sorgusu (`/api/v1/incidents/spatial-search`) — eski `app/api/v1/` buradan v2.4'te taşındı |
| `app/scrapers/ibb_ingestor.py` | İBB CKAN trafik duyuru ingestor'u |
| `alembic/` | Şema migrasyonları (baseline + dispatch/arrival/performans alanları uygulandı) |
| `frontend/static/geo/turkey-il.geojson` | 81 il sınırı (OSM, sadeleştirilmiş, ~225 KB) |
| `frontend/static/js/c4i.js` | Devriye katmanı (WS+polling), il choropleth, trend/koridor/prediktif/performans/kapsama panelleri |
| `app/ui/admin.py` | Admin panel — sevk kuyruğu kartı + İBB tetikleme butonu |
| `scripts/` | Bağımsız CLI araçları (bkz. "Yardımcı Scriptler" bölümü) — `pytest`'e dahil değil |

## Veri Modeli Notları

- `crime_events.incident_type`: `crime | traffic_accident | fire_anomaly`
- `crime_events.assigned_unit_id` / `resolved_at`: dispatch durumu (NULL=bekliyor)
- Migration: **Alembic aktif** (`alembic/env.py`, geoalchemy2 helper'ları ile PostGIS/tiger
  uzantı tabloları autogenerate'den filtrelenir). Yeni model değişikliğinden sonra:
  `python -m alembic revision --autogenerate -m "..."` → `python run.py migrate`.
  Eski `main.py` lifespan'deki `ADD COLUMN IF NOT EXISTS` satırları geriye dönük uyumluluk
  için duruyor (zaten deploy edilmiş DB'ler için) — yeni şema değişiklikleri artık Alembic'te.
- Devriye birimleri açılışta tablo boşsa `seed_police_units()` ile oluşturulur.
  Sıfırlamak için: `POST /api/v1/units/seed` (admin).

## Çalıştırma

```bash
python run.py            # Docker Compose ile DB + app'i kaldırır (build dahil)
python run.py restart    # kod degisikliginden sonra KULLAN — image'i yeniden build eder
python run.py migrate    # alembic upgrade head (yeni migration'i uygular)
python run.py local      # Docker'daki app'i durdurup lokal uvicorn (DB docker'da kalabilir)
```

- Harita: `http://localhost:8000/map` · Admin: `/admin` · API docs: `/api/docs`
- Demo/mock veri sistemi **yok** (v2.1'de kaldırıldı). Veri: `POST /scrape` (OSINT) veya
  `POST /ingest/ibb` (resmi trafik, admin).

## Yardımcı Scriptler (`scripts/`)

Bunlar `pytest`'in parçası değil — çalışan bir instance'a karşı manuel/CLI diagnostik araçları:

| Script | Ne yapar |
|---|---|
| `smoke_test.py [BASE_URL]` | Çalışan instance'a karşı hızlı uçtan uca sağlık kontrolü |
| `diagnose_sources.py` | Her OSINT kaynağını (GDELT/RSS/Telegram) tek tek test edip `ingestion_report.json` üretir |
| `probe_telegram.py [OUT_FILE]` | Telegram kanal adaylarının hangisinin canlı olduğunu tarar |
| `run_scrape_poll.py` | `/scrape` tetikler, `/scraper/metrics`'i bitene kadar izler |
| `normalize_crime_db.py` | Mevcut `crime_events` kayıtlarını normalize eder (kategori + konum) |

## Analitik Kuralları

- **Trends** (`/analytics/trends`): son 7g vs önceki 7g, şehir bazında; `change_pct >= +20` → rising.
  `per_100k` alanı TÜİK 2025 nüfusuna göre normalize sayı.
- **Critical** (`/analytics/critical`): son 1 saat, `severity_score >= 7`.
- **Corridors** (`/analytics/corridors`): son 7g, `severity >= 6` yoğunluğu → `risk_score = n × ort_şiddet / 10`, artı `per_100k`.
- **Predictive** (`/analytics/predictive`) — **ML modeli DEĞİL**, kural-tabanlı erken uyarı:
  `score = 100 × (0.45×yoğunluk_sapması + 0.30×trend + 0.25×ort_şiddet)`. Metodoloji notu
  `app/modules/c4i/predictive.py` docstring'inde — veri hacmi arttıkça gerçek saat/gün
  mevsimselliği modeline (Poisson regresyon vb.) geçiş öneriliyor.

## Dispatch Akışı (v2.3)

1. Her ~15 sn (`DISPATCH_SWEEP_EVERY_N_TICKS`), son 30 dk + şiddet≥7 + `assigned_unit_id IS NULL`
   olaylar **öncelik puanına** göre sıralanır: `severity + min(age_min/5×0.5, 3.0)` — starvation önleme.
2. En yakın "patrolling" birim haversine ile bulunur, DB'de atomik `UPDATE ... WHERE assigned_unit_id IS NULL` ile atanır (yarış durumuna dayanıklı).
3. Birim `mode:"dispatch"` rotasında 90 km/s ile olay yerine gider.
4. Varışta `mode:"onscene"` — 45-150 sn sabit bekler (mücadele süresi simülasyonu).
5. Süre dolunca `crime_events.resolved_at` doldurulur, birim yeni devriye rotasıyla döner.
6. Manuel kapatma: `POST /api/v1/incidents/{id}/resolve` (admin) — Admin panelindeki
   **Sevk Kuyruğu** kartından "Kapat" butonuyla de tetiklenebilir.
7. Kuyruk görünümü: `GET /api/v1/incidents/queue` (pending/assigned, öncelik, ETA).

## Choropleth (İl Sınırları)

- `frontend/static/geo/turkey-il.geojson`: OSM tabanlı (`izzetkalic/geojsons-of-turkey`, ODbL),
  81 il, `shapely.simplify(0.008)` ile sadeleştirilmiş (~225 KB, GZip ile daha küçük).
  `properties.il` anahtarı `CITY_COORDS`/`POPULATION_2025` ile birebir eşleşir (Türkçe karakter
  normalizasyonu: İ/I/ı/â/î/û gibi OSM'deki tüm varyantlar test edilip eşleştirildi).
- Frontend'de statik olarak bir kez yüklenir, `/analytics/trends` ile il adına göre
  client-side birleştirilir (`c4i.js > renderRiskChoropleth`). Renk: rising=kırmızı,
  falling=yeşil, stable/veri yok=gri (neredeyse şeffaf).
- **Bilinen boşluk:** Bu il (province) düzeyinde, ilçe (district) düzeyinde değil — kullanıcı
  "ilçe bazlı" istemişti ama ilçe sınırları (~970 poligon) çok daha ağır/karmaşık; il düzeyi
  pratik bir ara adım olarak seçildi. İlçe geçişi için aynı kaynaktaki `admin-level-6` dosyası kullanılabilir.

## Nüfus Verisi

`app/modules/crime/population.py` — TÜİK ADNKS 2025, 81 il, toplam ~86.1M (kaynak: TÜİK/Wikipedia
çapraz doğrulama). `CITY_COORDS` ile tam örtüşüyor — bu sırada **5 eksik il** (Aksaray, Ardahan,
Bartın, Batman, Bayburt) `app/modules/crime/services.py`'ye eklendi; bu iller 1990'larda kurulmuştu
ve önceden OSINT geolocation'da hiç tanınmıyorlardı (haberlerde geçseler bile başka bir ile
düşüyor ya da atlanıyor olabilirdi) — bu bir veri kalitesi düzeltmesiydi, yan bulgu.

## İBB Veri Kaynağı Notu

`resource_id=1c043914-8a76-4793-bae9-c60a68c7d389` hâlâ tek/güncel kaynak; farklı bir resource
bulunamadı ama en yeni kayıt **2025-03-05** tarihli (148k kayıt) — veri seti o tarihten beri
görünürde beslenmiyor olabilir. Detay: `docs/VERI_KAYNAKLARI.md` §0. Ayrı bir "Trafik Yoğunluk
Haritası" veri seti bulundu (farklı şema — yoğunluk/hız, olay değil) — gelecekte ayrı katman olabilir.

## v2.4'te Eklenenler (2026-07-13)

- **`crime_events` yeni alanlar:** `dispatched_at` (sevk anı, `dispatch.py > auto_dispatch`'te
  set edilir), `arrived_at` (sahne varış anı, `simulation.py`'daki dispatch→onscene geçişinde
  set edilir). `resolved_at` zaten vardı. Bu 4 zaman damgası (+ `timestamp`) performans
  KPI'larının tüm temelidir.
- **`GET /api/v1/analytics/performance`** (`app/modules/c4i/performance.py`): sevk gecikmesi,
  seyahat süresi, sahne süresi, toplam müdahale süresi — avg/median/p90, genel + şehir bazlı +
  birim bazlı. Saf fonksiyonlar (`compute_incident_durations`, `summarize_durations`,
  `build_performance_report`) DB'den bağımsız test edilebilir. Sidebar'da "Ort. Müdahale" KPI
  kutusu + "Müdahale Performansı" detay paneli.
- **`GET /api/v1/analytics/coverage`** (`app/modules/c4i/coverage.py`): son N gündeki önemli
  olayların en yakın **güncel** devriye birimine mesafesi (haversine) → şehir bazlı
  `gap_score = olay_sayısı × ort_şiddet × ort_mesafe / 10`. Canlı testte Şırnak (birim yok,
  ~200km) gap_score 366 ile İstanbul'un (4.5) çok üstünde doğru tespit edildi. Sidebar'da
  "Kapsama Boşlukları" paneli. **Metodoloji notu:** tarihsel değil güncel birim konumu
  kullanılır — kesin analiz için `police_unit_history` ile olay zamanına en yakın kayıt
  eşleştirilmeli (yol haritasında).
- 9 yeni test (`test_c4i.py`), toplam 65.

## Yol Haritası (sıradaki işler — hiçbiri acil değil, öneri sırasıyla)

1. [ ] Kapsama boşluğu analizini `police_unit_history` ile tarihsel konuma bağla (şu an güncel konum kullanıyor — yaklaşıklık)
2. [ ] İlçe bazlı choropleth'e geçiş (admin-level-6 kaynağı, ~970 poligon — performans testi gerekir)
3. [ ] WS için tek yayıncı (broadcast) mimarisi — şu an istemci başına ayrı DB sorgusu var
4. [ ] Prediktif skoru gerçek saat/gün mevsimselliğine taşı (veri hacmi yeterince büyüyünce)
5. [ ] Dispatch: aynı anda birden fazla birim gerektiren olaylar (çoklu-birim sevk)
6. [ ] İBB veri setinin canlılığını periyodik izleyen bir "veri tazeliği" uyarısı
7. [ ] `police_unit_history` üzerinden ısı haritası / yoğunluk analizi (iz verisi birikince)
8. [ ] Performans KPI'ları admin panelinde de göster (şu an sadece harita sidebar'ında)

## Proje Düzeni (v2.4 dosya yapısı denetimi, 2026-07-13)

- **Git artık aktif** — proje daha önce git deposu değildi, büyük bir dosya-yapısı temizliği
  öncesi güvenlik ağı olarak `git init` yapıldı. `.env` doğru şekilde `.gitignore`'da, commit
  edilmedi (doğrulandı). Bundan sonraki değişiklikler için normal git iş akışı kullanılabilir
  (kullanıcı istemeden otomatik commit atma — bkz. genel talimatlar).
- **`app/api/` kaldırıldı:** Tek dosyası olan `spatial.py`, tutarlılık için
  `app/modules/crime/spatial.py`'ye taşındı — artık her şey `app/modules/<domain>/` altında.
- **`scripts/test_ingestion.py` → `scripts/diagnose_sources.py`:** İsim `test_*.py` pytest
  deseniyle çakışıyordu (bare `pytest` komutu yanlışlıkla toplamaya çalışırdı). `pytest.ini`'ye
  ayrıca `testpaths = tests` eklendi (savunma katmanı).
- **Kod tabanında gerçek "ölü dosya" bulunamadı** — `app/` altındaki her modül en az bir yerden
  import ediliyor (sistematik olarak doğrulandı). v2.1'de zaten `.cursor/`, boş `.github/`,
  demo/mock sistemi temizlenmişti; bu turda ek bir kod artığı çıkmadı.
- **`docs/TRIA_Bitirme_Raporu.md` ve `Görseller/*.png`'ye DOKUNULMADI:** Bunlar kullanıcının
  akademik tez içeriği/ekran görüntüleri — hâlâ pre-C4I mimariyi anlatıyor (eski isim "Türkiye
  Risk İstihbarat Ağı", Time Slider/Draw&Search gibi artık var olmayan özellikler), yani
  güncel değil. Ancak bunlar kod artığı değil, kullanıcının kendi yazdığı rapor — silinmedi/
  değiştirilmedi. Kullanıcı isterse ayrı bir görev olarak C4I mimarisine göre güncellenebilir.
- Bağımlılıklar (`requirements.txt`/`requirements-dev.txt`) kod tabanındaki gerçek import'larla
  bire bir karşılaştırıldı — eksik/fazla paket yok.

## Bilinen Kısıtlar

- ⚠️ **Çift instance uyarısı:** Docker'daki `tria_app` ile lokal `uvicorn` aynı anda çalışırsa
  iki simülasyon aynı `police_units` tablosunu ezer. Lokal geliştirmede `docker stop tria_app`,
  yalnızca `database` konteynerini kullan. Kod güncellemesi sonrası `python run.py restart`.
- Devriye hareketi simülasyondur (gerçek AVL/GPS beslemesi yok) — API sözleşmesi gerçek
  besleme ile uyumlu tasarlandı (aynı `/units` ve `/ws/units` sözleşmesi korunarak değiştirilebilir).
- Choropleth il düzeyinde (ilçe değil) — yukarıda not edildi.
- Prediktif skor ML modeli değil, şeffaf kural-tabanlı formül — `predictive.py` docstring'i şart koşuyor.
- `.env` içinde GROQ_API_KEY, TELEGRAM_* anahtarları var — repoya commit etme.

# TRIA C4I — Gerçek Zamanlı Kolluk İstihbarat Ağı

> **Proje durumu (son güncelleme: 2026-07-15, v2.8):** Platform **81 ilin tamamına** genişletildi
> (önceden yalnızca 11 büyükşehir + Amasya tohumlanıyordu) — tohum devriye verisi TÜİK nüfusuna
> orantılı üretiliyor, resmi 81 il plaka kodu tablosu ve `turkey-ilce.geojson`'dan türetilen
> ilçe listeleri eklendi. Harita/admin panelindeki il-ilçe filtre dropdown'ları artık hardcode
> değil, yeni `GET /geo/cities` + `GET /geo/districts` uçlarından dinamik dolduruluyor. Güvenlik
> puan kartı artık gerçek bir **ulusal özet**: veri üretmeyen iller de `has_data=false` ile
> listede kalıyor (soluk gösteriliyor), sadece olay/devriye kaydı olan birkaç il değil. **Bu faz
> bilinçli olarak simülasyon/varsayım verisiyle inşa edildi** — gerçek 112/155 çağrı merkezi,
> AVL/GPS, kamera/ANPR entegrasyonu vb. henüz yok (bkz. Bilinen Kısıtlar); amaç gerçek
> entegrasyonlara hazır, ikna edici bir ulusal tasarım ortaya koymak.
> **88 test** geçiyor.

## v2.8 — Ulusal Kapsama: 81 İl Tohum Verisi, Dinamik İl/İlçe API'si, Ulusal Puan Kartı (2026-07-15)

- **81 il tohum verisi** (`app/modules/c4i/simulation.py`): `SEED_PLAN` artık elle seçilmiş
  11 şehir yerine `POPULATION_2025`'e orantılı hesaplanıyor (`min(10, max(2, pop/1.5M))` —
  toplam 173 birim, en kalabalık il İstanbul 10 birimle tavanda). `PLATE_CODES` resmi 81 il
  trafik plaka kodu tablosuyla tamamlandı. `CITY_DISTRICTS` artık elle yazılmış 4 şehir değil,
  `district_lookup.list_districts()` ile `turkey-ilce.geojson`'dan türetiliyor (76/81 il bu
  kaynakta var, kalan 5 il — Iğdır/Karabük/Kırşehir/Rize/Trabzon — tek "Merkez" ilçesine düşüyor,
  mevcut fallback davranışı korunuyor).
- **`district_lookup.list_districts(city)`** (yeni): normalize edilmiş (OSM'deki "X merkez" →
  kanonik "Merkez"), alfabetik, tekilleştirilmiş ilçe listesi — hem seed hem yeni `/geo/districts`
  ucu bu tek kaynağı paylaşıyor.
- **`population.py > IL_LABELS_TR`** (yeni): 81 il için doğru Türkçe görünen ad (büyük/küçük
  harf, noktalı/noktasız I ayrımı) — `POPULATION_2025` ile bire bir aynı 81 anahtar.
- **Yeni uçlar:** `GET /api/v1/geo/cities` (81 il, Türkçe alfabetik) ve
  `GET /api/v1/geo/districts?city=` (o ilin ilçeleri) — public, auth gerekmiyor (statik referans
  veri). `frontend/static/js/c4i.js > initRegionFilters` artık bu iki uçtan dinamik dolduruluyor;
  eskiden yalnızca 11 il / 4 il için hardcode edilmiş `CITY_LABELS`/`CITY_DISTRICTS` objeleri
  kaldırıldı. `initAuthWidget` artık `initRegionFilters()`'ın (async) tamamlanmasını bekliyor —
  aksi halde `city_operator` girişinde il dropdown'ı henüz dolmadan filtre kilitlenmeye
  çalışılıyordu.
- **`scorecard.py > build_scorecard`**: taban şehir kümesi artık yalnızca veri üreten şehirler
  değil, `POPULATION_2025`'in tamamı (81 il) — her satırda yeni `has_data` alanı var. Sıralama
  `(has_data, risk_index)` — veri olanlar önce, veri olmayanlar (henüz olay/devriye kaydı yok)
  listenin sonuna düşüyor ama **listeden düşmüyor**. Admin panelindeki puan kartı bu satırları
  soluk + "Veri yok" etiketiyle gösteriyor (`app/ui/admin.py > loadScorecard`), üstte
  "X / 81 ilde veri var" özeti eklendi.
- **Bilinçli tasarım kararı:** Amasya'nın önceki "5 birim / 5 tür / 5 ilçe" özel referans
  senaryosu (bkz. v2.5) kaldırıldı — artık nüfus formülüne göre 2 birim alıyor, tıpkı benzer
  büyüklükteki diğer iller gibi. Tekil "flagship" örnek yerine tekdüze/tutarlı ulusal formül
  tercih edildi; İstanbul (10 birim, en fazla tür çeşitliliği) çoklu-birim/tür senaryoları için
  artık daha iyi bir örnek.
- 5 yeni test (83→88): `SEED_PLAN`/`PLATE_CODES`/`IL_LABELS_TR`'nin 81 ili tam kapsadığı,
  `build_scorecard`'ın `has_data` davranışı, `list_districts` normalizasyonu.
- **Bu fazın kapsamı dışında (bilinçli):** gerçek veri/API entegrasyonları (112/155 çağrı
  merkezi, AVL/GPS, kamera/ANPR, UYAP) — kullanıcıyla konuşulup ertelendi, şimdilik tasarım/
  özellik geliştirmesi simülasyon verisiyle sürüyor (bkz. Yol Haritası).

## v2.7 — Otomatik İlçe Ataması, Tür-Çeşitli Sevk, Tarihsel Kapsama, Puan Kartı, Mevsimsel Analiz (2026-07-13)

- **Otomatik ilçe ataması** (`app/modules/crime/district_lookup.py`): `turkey-ilce.geojson`
  kullanarak point-in-polygon (shapely — yeni bağımlılık, requirements.txt'e eklendi).
  `scraper.py`, `ibb_ingestor.py` ve `report_incident` (boş bırakılırsa) artık district'i
  otomatik dolduruyor. `POST /normalize-data` mevcut kayıtları da geriye dönük dolduruyor —
  canlı testte 230 kayıttan 209'u dolduruldu (ör. İstanbul: Fatih, Küçükçekmece, Bakırköy...).
- **Çoklu-birim sevkte tür çeşitliliği** (`dispatch.py > select_next_unit`): 2. birim seçilirken
  1. birimden FARKLI türde (ör. asayiş+TEM) olan en yakın birim tercih edilir; uygun tür yoksa
  en yakına düşülür. Canlı testte doğrulandı (TEM + Trafik karışık sevk).
- **Kapsama boşluğu tarihselleştirildi**: `coverage_gaps` artık her olay için
  `police_unit_history`'den olay ANINDAKİ birim konumlarını (`LATERAL` + `DISTINCT ON` "asof"
  eşleştirme) kullanıyor, güncel konuma yalnızca tarihsel kaydı olmayan olaylar için düşüyor
  (`historical_match_count`/`current_position_fallback_count` ile şeffaf). Yeni bileşik indeks:
  `police_unit_history(unit_id, recorded_at DESC)`. Canlı testte 49/49 olay tarihsel eşleşti.
- **Güvenlik puan kartı** (`GET /analytics/scorecard`, `app/modules/c4i/scorecard.py`, sadece
  admin): mü­dahale süresi + kapsama boşluğu + 7g trendin ağırlıklı toplamından `risk_index` —
  **bilimsel kesin skor değil**, iller arası hızlı karşılaştırma. Admin panelinde tablo.
- **Mevsimsel/geçmiş suç istatistiği** (`GET /analytics/seasonal`, `app/modules/c4i/seasonal.py`):
  aylık dağılım + yaz ayları (Haz-Ağu) vs diğer aylar karşılaştırması, kategori/şehir bazlı.
  **Önemli metodoloji notu**: gerçek mevsimsellik değil — mevcut veri seti yalnızca birkaç ay
  kapsadığı için (canlı testte Mart+Temmuz), "yaz-dışı taban=0" olan kategoriler **riser
  sayılmıyor** (`rest_avg_per_month > 0` şartı eklendi — aksi halde her kategori yanıltıcı
  şekilde "+100%" görünüyordu, çünkü veri sadece yaz ayında var, gerçekte artış yok). Bu bilinçli
  bir düzeltmeydi: ilk versiyon canlı testte yanıltıcı sonuç verdi, fark edilip düzeltildi.
  Gerçek mevsimsellik tespiti için birden fazla yılın verisi gerekiyor (predictive.py'deki
  "veri hacmi arttıkça güvenilir hale gelir" notuyla aynı ruh).
- 9 yeni test (75→83... toplam 83), hepsi Docker'da canlı API çağrılarıyla da doğrulandı.

**Telegram bildirim kaldırıldı:** `app/modules/crime/alerts.py` tamamen silindi, `/test/telegram`
endpoint'i ve admin panelindeki "Telegram test" butonu kaldırıldı, `.env`'deki `TELEGRAM_BOT_TOKEN`/
`TELEGRAM_CHAT_ID`/`TELEGRAM_GLOBAL_*`/`TELEGRAM_ALERT_*` değişkenleri silindi. **Telegram OSINT
kaynak taraması (`telegram_preview.py`, `sources_config.py`, `scripts/probe_telegram.py`) dokunulmadan
kaldı** — bu iki özellik birbirinden bağımsızdı, sadece `scraper.py`'deki `SCRAPER_METRICS.alerts_sent`
ve `get_pipeline_diagnostics().alerts` alanları kaldırıldı.

**Auth/rol sistemi (`app/modules/auth/`):** `users` tablosu (`username`, `password_hash` — PBKDF2,
`role`: admin|city_operator, `city`). Token: stdlib `hmac`+`hashlib` ile imzalanmış base64 payload
(JWT değil ama aynı işlevi görüyor, ek pip bağımlılığı yok — bkz. `security.py`). 3 demo hesap
otomatik seed edilir (`admin`/`amasya_asayis`/`istanbul_asayis`, şifreler `.env`'de `DEMO_*_PASSWORD`
ile özelleştirilebilir, varsayılan `<kullanıcı>123`). `/login` sayfası, `POST /api/v1/auth/login`.
- **Şehir kısıtlaması sunucu tarafında zorunlu**: `city_operator` girişi yapan biri `/units`,
  `/geojson`, `/stats`, `/analytics/*`, `/ws/units` (token query param ile — tarayıcı WS custom
  header göndermiyor) üzerinden yalnızca KENDİ ilinin verisini görür (istemci filtresi değil,
  `app/core/auth.py > scope_city_for` + her router'da SQL WHERE koşulu).
  - `require_admin`: eskisi gibi çalışıyor (X-Admin-Key veya boşsa açık) + admin-rollü token da kabul eder.
  - `require_write_access` (yeni, `/incidents/report` + `/incidents/{id}/resolve`): admin veya
    city_operator (kendi iliyle sınırlı) — `city_operator` başka ile ihbar giremez/olay kapatamaz (403).
- Frontend: harita + admin panelinde giriş/çıkış widget'ı, `city_operator` için il seçici kilitleniyor
  ve ihbar formundaki il alanı otomatik dolduruluyor.
- **Bilinçli sınırlama:** hâlâ tek `ADMIN_API_KEY` de sistem-geneli admin işlemlerine (seed/clear/
  ibb ingest/groq test) erişebiliyor — gerçek kurumsal devreye alışta bu kaldırılıp yalnızca
  rol-bazlı girişe geçilmeli.

**İlçe düzeyinde choropleth:** `izzetkalic/geojsons-of-turkey` deposundaki `turkey-admin-level-6.geojson`
(Git LFS, ~45MB ham OSM verisi) indirilip il plaka koduna (`network: "TRxx-districts"` → resmi 81 il
plaka kodu tablosu) göre `il`/`ilce` alanlarıyla etiketlendi, `shapely.simplify(0.004)` ile küçültüldü
→ **928 ilçe poligonu, ~1.27MB** (`frontend/static/geo/turkey-ilce.geojson`). Bir il seçilince harita
o ilin ilçelerini olay yoğunluğuna göre renklendirir (il düzeyi choropleth o an gizlenir), devriyesiz
ilçeler kırmızı kenarlıkla vurgulanır. "Merkez" ilçe adı eşleştirmesi normalize ediliyor (OSM'de
"X merkez" formatında, bizim tohum verimizde "Merkez").

**Çoklu-birim sevk (`app/modules/c4i/dispatch.py > compute_required_units`):** şiddet ≥9.0 olaylara
2 birim aynı anda sevk edilir. `crime_events.required_units` + `assigned_unit_ids` (JSONB, **kümülatif**
— asla eksiltilmez, `auto_dispatch` "kaç birim daha gerekli" hesabını bu listenin uzunluğuna göre yapar).
Çözülme (`resolved_at`), o an fiilen sahada/yolda başka birim kalmadığında dolar (in-memory kontrol,
bkz. `simulation.py > simulation_tick`).
- **Dinamik doğrulama sırasında bulunan 2 gerçek hata (statik incelemeyle yakalanmazdı):**
  1. İlk versiyon `assigned_unit_ids`'i bir birim işini bitirince listeden **eksiltiyordu** — bu,
     2 birimden biri erken bitirince sistemin "hâlâ 1 birim eksik" sanıp **az önce dönen aynı birimi
     aynı olaya tekrar sevk etmesine** yol açtı (canlı logda yakalandı: `EKIP-34-04` #249'u bitirip
     saniyeler içinde tekrar #249'a sevk edildi). Düzeltme: liste kümülatif hale getirildi, çözülme
     kontrolü ayrı bir in-memory "başka aktif birim var mı" mantığına taşındı.
  2. `resolve_incident`'ta `UPDATE ... SET assigned_unit_ids=[] ... RETURNING assigned_unit_ids` —
     PostgreSQL `RETURNING` **güncelleme SONRASI** değeri döndürür, bu yüzden fonksiyon her zaman
     boş liste görüyordu ve manuel "Kapat" ikinci birimi asla serbest bırakmıyordu. Düzeltme: eski
     değer UPDATE'ten ÖNCE ayrı bir SELECT ile okunuyor.
  Her ikisi de gerçek Docker ortamında canlı sevk döngüsü izlenerek (curl + docker logs + DB sorgusu,
  dakikalarca) yakalandı — pytest'teki saf fonksiyon testleri bu zamanlamaya bağlı etkileşim
  hatalarını yakalayamazdı, bu yüzden yeni operasyonel özelliklerde canlı uçtan uca izleme şart.

**Test:** 69 pytest (compute_required_units, district_for, unit_types + öncekiler), ek olarak
Playwright ile auth/il-ilçe filtresi/ihbar girişi uçtan uca, ve çoklu-birim sevk canlı Docker'da
dakikalarca izlenerek (curl+docker logs+psql) doğrulandı.

## v2.5 — Çok Şehirli Asayiş Platformu Pivotu (2026-07-13)

Kullanıcı projeyi artık gerçek bir asayiş platformu olarak konumlandırdığını belirtti: her il/ilçe
kendi devriye birimlerini (asayiş/trafik/TEM/yunus/çevik kuvvet) türüne göre haritada görecek,
gelen ihbar anında sisteme düşüp aktif olay olarak görünecek, bölge bazlı suç/trafik dağılımı
izlenecek. Referans senaryo: **Amasya → Merzifon** (`docs/PLAN_ASAYIS_PLATFORMU.md`). Gerçek veri
entegrasyonunu ilgili kurumlar yapacak — bu fazın hedefi **sistemin mantığını** ikna edici şekilde
göstermek; bu yüzden auth/production-hardening bilinçli olarak ertelendi (bkz. Bilinen Kısıtlar).

**Veri modeli:**
- `police_units.district`, `crime_events.district` eklendi (Alembic `a3f7c9d2e1b4`).
- `unit_type` sözlüğü genişledi: `asayis | trafik | tem | yunus | cevik_kuvvet`
  (`app/modules/c4i/models.py > UNIT_TYPES`). Eski `patrol_car`/`motorcycle` değerleri geriye
  dönük uyumluluk için frontend'de otomatik eşleniyor.
- `simulation.py`: Amasya tohum verisi (5 birim, 5 farklı tür, 5 farklı ilçe — Merkez/Merzifon/
  Suluova/Taşova/Gümüşhacıköy) + `CITY_DISTRICTS` haritası (istanbul/ankara/izmir/amasya).

**Yeni uç noktalar (`app/modules/c4i/router.py`):**
- `POST /api/v1/incidents/report` — çağrı merkezi/dispatcher ihbar girişi (OSINT kazımadan
  bağımsız doğrudan kanal). `lat`/`lon` opsiyonel — boş bırakılırsa şehir merkezi + hafif rastgele
  sapma kullanılır. Otomatik dispatch kuyruğuna girer (mevcut v2.3 akışı).
- `GET /api/v1/analytics/breakdown?city=&district=` — seçili bölge için suç türü + olay tipi
  dağılımı (Faz 4).
- `/units`, `/geojson` artık `district` alanını da döndürüyor; `/geojson` ayrıca `resolved`
  (çözülmüş mü) bilgisini de döndürüyor.
- `GET /api/v1/analytics/districts?city=` — seçili ildeki **tüm ilçelerin** yan yana listesi
  (olay sayısı + ort. şiddet + aktif devriye sayısı), olay sayısına göre sıralı. Sidebar'da
  "İlçe Listesi" paneli — satıra tıklamak `filterDistrict`'i o ilçeye ayarlayıp drill-down yapar.

**Frontend — tamamen yeniden tasarım ("operasyon konsolu" / CAD-NOC estetiği):**
- `app/ui/theme.py`, `frontend/static/css/map.css`: eski neon-glow/blur/gradient "cyberpunk
  dashboard" görünümü kaldırıldı; düz paneller, ince kenarlık, renk yalnızca durum anlamı taşıyor
  (amber `#e8a33d` tek vurgu rengi). Tipografi: Oswald (başlık) + Inter (gövde) + JetBrains Mono
  (veri/kod). İmza motifi: devriye/olay satırlarında "annunciator" tarzı kare durum lambası.
- CBS haritası sidebar'ı sadeleştirildi: önceden 8+ hep-açık panel vardı, şimdi `<details>` ile
  gruplandı (Analitik ve Görünüm&Filtreler varsayılan kapalı). Yeni: İl/İlçe/Birim-tipi filtresi
  (client-side, `c4i.js > initRegionFilters`), Bölge Analizi paneli, haritadan doğrudan İhbar Gir
  formu, canlı saat + WS bağlantı lambası, yeni kritik olay geldiğinde KPI kutusunun flaşlaması.
- Admin paneli sadeleştirildi: Geliştirici/API testleri artık varsayılan kapalı `<details>`
  içinde; "Yeni İhbar Gir" formu eklendi.
- Çözülmüş olaylar haritada soluk/gri gösteriliyor (`resolved` alanı), aktif+kritik olaylar
  pulse animasyonu koruyor.

**Doğrulama:** Playwright ile hem `/map` hem `/admin` uçtan uca test edildi — il/ilçe filtresi,
birim tipi filtresi, bölge analizi paneli, harita ve admin üzerinden ihbar girişi, WS lambası,
konsol hatası kontrolü. 12/12 kontrol geçti, test verileri temizlendi. `tests/test_c4i.py`'ye
`_district_for` ve `UNIT_TYPES` için 3 yeni birim testi eklendi (68 test).

**Ertelenenler (bkz. `docs/PLAN_ASAYIS_PLATFORMU.md` §5, §7):** gerçek kullanıcı auth/rol sistemi,
tam Türkiye mahalle poligon choropleth'i (ücretsiz kaynak yok), ilçe düzeyinde choropleth (veri
edinimi ayrı iş).

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
| `app/modules/c4i/models.py` | `police_units` (+ `district`, `unit_type` sözlüğü), `police_unit_history` (iz sürme) |
| `app/modules/c4i/simulation.py` | 3 sn tick: patrol/dispatch/onscene 3 modlu hareket motoru + 60 sn'de bir geçmiş snapshot |
| `app/modules/c4i/dispatch.py` | Öncelik kuyruğu, haversine, ETA, çoklu-birim atama (`select_next_unit` — tür çeşitliliği), `assigned_unit_ids` (kümülatif) |
| `app/modules/c4i/predictive.py` | Kural-tabanlı erken uyarı skoru (bkz. Prediktif Risk bölümü) |
| `app/modules/c4i/performance.py` | Sevk gecikmesi/seyahat/sahne/toplam müdahale süresi KPI'ları (saf fonksiyonlar) |
| `app/modules/c4i/coverage.py` | Kapsama boşluğu skoru — artık `police_unit_history` ile tarihsel eşleştirme (bkz. router.py) |
| `app/modules/c4i/scorecard.py` | İller arası karşılaştırmalı `risk_index` (saf fonksiyon, `/analytics/scorecard`) |
| `app/modules/c4i/seasonal.py` | Aylık dağılım + yaz ayları karşılaştırması (saf fonksiyon, `/analytics/seasonal`) |
| `app/modules/crime/district_lookup.py` | `turkey-ilce.geojson` ile point-in-polygon ilçe çözümleme (shapely) |
| `app/modules/c4i/router.py` | `/units`, `/ws/units`, `/units/{id}/history`, `/analytics/*` (+ `breakdown`/`districts`/`scorecard`/`seasonal`), `/incidents/queue`, `/incidents/report`, `/incidents/{id}/resolve` |
| `app/modules/crime/spatial.py` | PostGIS çokgen/yarıçap sorgusu (`/api/v1/incidents/spatial-search`) — eski `app/api/v1/` buradan v2.4'te taşındı |
| `app/modules/auth/` | `users` tablosu, PBKDF2 hash + imzalı token (`security.py`), `/api/v1/auth/login`, demo hesap seed |
| `app/scrapers/ibb_ingestor.py` | İBB CKAN trafik duyuru ingestor'u |
| `alembic/` | Şema migrasyonları (baseline + dispatch/arrival/performans/district/users/çoklu-birim alanları uygulandı) |
| `frontend/static/geo/turkey-il.geojson` | 81 il sınırı (OSM, sadeleştirilmiş, ~225 KB) |
| `frontend/static/geo/turkey-ilce.geojson` | 928 ilçe sınırı (OSM admin-level-6, sadeleştirilmiş, ~1.27 MB) |
| `frontend/static/js/c4i.js` | Devriye katmanı (WS+polling), il/ilçe choropleth, bölge+birim-tipi filtresi, auth widget, trend/koridor/prediktif/performans/kapsama panelleri |
| `app/ui/admin.py` | Admin panel — sevk kuyruğu kartı, İBB tetikleme butonu, ihbar giriş formu, auth widget |
| `app/ui/login.py` | `/login` sayfası |
| `scripts/` | Bağımsız CLI araçları (bkz. "Yardımcı Scriptler" bölümü) — `pytest`'e dahil değil |

## Veri Modeli Notları

- `crime_events.incident_type`: `crime | traffic_accident | fire_anomaly`
- `crime_events.assigned_unit_id` / `resolved_at`: dispatch durumu (NULL=bekliyor)
- `crime_events.district`: manuel ihbarda dolar (OSINT/İBB'de henüz NULL — geocoding yok)
- `crime_events.required_units` / `assigned_unit_ids`: çoklu-birim sevk (bkz. v2.6 notu — `assigned_unit_ids` KÜMÜLATİF, asla eksiltilmez)
- `users.role` / `users.city`: admin (city=NULL, tüm iller) | city_operator (kendi iline sınırlı)
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

1. [ ] Auth sistemini sertleştir: `ADMIN_API_KEY` master-key fallback'i kaldır, yalnızca rol-bazlı
       girişe geç; demo hesapları gerçek kurumsal hesaplarla değiştir
2. [ ] Tam Türkiye mahalle poligon kaynağı bulunursa (ücretli/kurumsal) mahalle choropleth'i
3. [ ] WS için tek yayıncı (broadcast) mimarisi — şu an istemci başına ayrı DB sorgusu var
4. [ ] Prediktif skoru + mevsimsel analizi (`seasonal.py`) gerçek saat/gün/çoklu-yıl mevsimselliğine
       taşı (veri hacmi — özellikle birden fazla yaz sezonu — yeterince büyüyünce)
5. [ ] İBB veri setinin canlılığını periyodik izleyen bir "veri tazeliği" uyarısı
6. [ ] `police_unit_history` üzerinden ısı haritası / yoğunluk analizi (iz verisi birikince)
7. [ ] Performans KPI'ları admin panelinde de göster (güvenlik puan kartı orada ama ayrı bir şey —
       sevk gecikmesi/seyahat/sahne süresi detay KPI'ları hâlâ sadece harita sidebar'ında)
8. [x] ~~81 il için tohum verisi (birim/plaka/ilçe) + dinamik il/ilçe filtre API'si~~ — v2.8'de yapıldı
9. [ ] Personel/vardiya modeli (`police_units`'e personel ataması + gündüz/gece nöbet) — simülasyon
       verisiyle bile dispatch mantığına "o an nöbette mi" boyutu katar
10. [ ] Rol hiyerarşisi derinleştirme (il emniyet müdürü / ilçe amiri / merkez rolleri, gerçek
        SSO olmadan demo hesaplarla) — mevcut `admin`/`city_operator` ikilisinin ötesi
11. [ ] Audit log (kim ne zaman hangi olayı görüntüledi/kapattı) — dış entegrasyon gerektirmez,
        KVKK'ya hazırlık olarak şimdiden gerçek şekilde inşa edilebilir
12. [ ] Kritik/uzun süredir çözülmeyen olaylar için in-app eskalasyon/bildirim paneli
13. [ ] `police_unit_history` üzerinden çok-yıllı sentetik geçmiş veri üretici — `seasonal.py`/
        `predictive.py`'nin gerçek mevsimsellik notunu şimdiden test etmek için
14. [ ] Saha ekibi için responsive/mobil-optimize görünüm (`/field` gibi) — simüle GPS onayı +
        olay notu girişiyle gerçek mobil istemcinin sözleşmesini önceden şekillendirir

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
- Choropleth artık hem il hem ilçe düzeyinde (bir il seçilince ilçelere geçer) — mahalle düzeyi
  hâlâ yok (ücretsiz veri kaynağı bulunamadı, yukarıda not edildi).
- Prediktif skor ML modeli değil, şeffaf kural-tabanlı formül — `predictive.py` docstring'i şart koşuyor.
- `.env` içinde GROQ_API_KEY var — repoya commit etme. (Telegram bildirim anahtarları v2.6'da kaldırıldı.)
- **Auth kısmen sertleştirildi (v2.6), tam değil:** artık gerçek `users` tablosu + rol bazlı token var
  ve GET/POST endpoint'leri sunucu tarafında şehir bazlı kısıtlanıyor — ama `ADMIN_API_KEY` hâlâ
  sistem-geneli bir "master key" olarak çalışıyor (require_admin, geriye dönük uyumluluk için).
  Gerçek kurumsal kullanım öncesi bu master-key yolu kaldırılıp yalnızca role-bazlı girişe geçilmeli.
- `crime_events.district` şu an yalnızca `POST /incidents/report` (manuel ihbar) ile dolar;
  OSINT/İBB kaynaklı olaylarda `NULL` kalır (ilçe geocoding henüz yok — `turkey-ilce.geojson` mevcut
  olduğu için bu artık kolayca eklenebilir bir sonraki adım).

# TRIA C4I — Gerçek Zamanlı Kolluk İstihbarat Ağı

## v2.9.2 — Sekmeli Arayüz Reorganizasyonu (2026-07-16)

Harita sidebar'ı ve admin paneli, özellik sayısı arttıkça (v2.6-v2.9) tek sütunda üst üste
yığılan 10+ bölüme çıkmıştı. İkisi de sekmeli yapıya geçirildi — koyu renk paletine
dokunulmadı (kullanıcı tercihi), yalnızca bilgi mimarisi değişti:

- **Harita** (`frontend/templates/index.html`, `map.css`, `c4i.js`): sidebar artık
  Harita / Olaylar / Analitik üç sekmesi — başlık+KPI+sekme çubuğu+alt aksiyon butonları
  sabit kalır, yalnızca orta içerik alanı sekmeye göre değişir ve kendi içinde kaydırılır
  (flex column + `.tab-panel { flex:1; overflow-y:auto }`). "Olaylar" sekmesinde kritik
  olay+eskalasyon toplamını gösteren kırmızı rozet var. Tüm mevcut element ID'leri korundu,
  `c4i.js`'in geri kalanı değişmedi.
- **Admin paneli** (`app/ui/admin.py`): Operasyon / Analitik & Denetim / Geliştirici üç
  sekmesi — eskiden art arda büyüyen `<details>` listesi (Puan Kartı, Eskalasyonlar, Audit
  Log, API Testleri) artık mantıksal gruplarda. "Analitik & Denetim" sekmesinde eskalasyon
  sayısı rozeti var.
- **Bulunan gerçek CSS hatası:** `hidden` attribute'lu rozet elemanlarına `display:
  inline-flex` unconditionally uygulanmıştı — tarayıcının `[hidden]{display:none}` varsayılan
  kuralıyla AYNI özgüllükte (0,1,0) olduğu için sayfa `<style>` bloğundaki kural cascade'de
  sonra geldiğinden kazanıyordu, rozet 0 olsa bile görünür kalıyordu. `.tab-badge[hidden]`/
  `.admin-tab-badge[hidden] { display: none; }` ile düzeltildi. Playwright ile
  `getComputedStyle(el).display` okunarak doğrulandı.
- Playwright ile masaüstü+mobil, her sekme geçişi ayrı ayrı ekran görüntüsüyle doğrulandı,
  konsol hatasız. 101 test değişmeden geçiyor (saf frontend/IA değişikliği).

## v2.9.1 — Harita/Mobil Kullanılabilirlik Düzeltmeleri (2026-07-16)

Ekran görüntüsüyle denetlenince v2.8'in 81-il genişlemesinin fark edilmemiş üç yan etkisi
bulundu, hepsi düzeltildi:

- **Harita ulusal zoom'da okunmaz haldeydi**: 178 devriye birimi her zaman tekil ikon+etiketle
  gösteriliyordu (kümeleme yoktu, sadece olay marker'ları kümeleniyordu). `c4i.js > patrolLayer`
  artık zaten yüklü olan `leaflet.markercluster`'ı kullanıyor (`disableClusteringAtZoom: 11`) —
  ülke genelinde yeşil/kırmızı sayı baloncukları, bir ile girince tekil birim+etiket.
- **Mobilde harita tamamen kullanılamıyordu**: `map.css`'te hiç `@media` sorgusu yoktu, sidebar
  sabit genişlikte + kapatılamaz bir overlay olarak haritanın tamamını kaplıyordu. `@media
  (max-width:768px)` ile off-canvas + hamburger toggle (`#sidebarToggle`) eklendi.
- **`/field` giriş yapılmadan tüm ülkenin personelini döküyordu**: `GET /personnel` auth
  gerektirmiyor (bilinçli, bkz. v2.9) — ama sayfa bunu kontrolsüz render ediyordu, sonuç 356
  kişilik tek sütun liste (~21.000px sayfa boyu). `field.py` artık `getAuth()` yoksa "giriş
  yapın" mesajı gösteriyor, kapsam-sız roller için de 40 kişilik görüntüleme tavanı var.

Playwright ile masaüstü + mobil ekran görüntüsü karşılaştırmasıyla doğrulandı (önce/sonra).
Test sayısı değişmedi (101) — bunlar saf frontend/UX düzeltmeleri.

> **Proje durumu (son güncelleme: 2026-07-16, v2.9):** Rol hiyerarşisi derinleşti (**ilçe_amiri**
> + **merkez** salt-okunur rolü), her devriye birimine **personel/vardiya** (gündüz/gece) atandı,
> tüm yazma işlemleri artık **audit log**'a düşüyor, uzun süredir çözülmeyen/eksik birimli kritik
> olaylar için **eskalasyon paneli** eklendi, `seasonal.py`'nin çok-yıl varsayımını test etmek
> için **sentetik geçmiş veri üreticisi** (`scripts/`) yazıldı, ve saha ekipleri için mobil
> optimize bir **`/field`** görünümü eklendi. **101 test** geçiyor. **Bu faz de bilinçli olarak
> simülasyon/varsayım verisiyle inşa edildi** — gerçek personel/kimlik/SMS entegrasyonu yok,
> hepsi mevcut mimarinin üzerine "gerçeğe bağlanmaya hazır" bir katman (bkz. Bilinen Kısıtlar).

## v2.9 — Personel/Vardiya, Rol Hiyerarşisi, Audit Log, Eskalasyon, Sentetik Veri, Saha Görünümü (2026-07-16)

- **Personel/vardiya modeli** (`app/modules/c4i/models.py > Personnel`, `simulation.py >
  seed_personnel`/`current_shift`): her devriye birimine 2 personel atanıyor (gündüz 08:00-20:00
  TRT + gece 20:00-08:00 TRT, sabit iki vardiyalı basit model). **Salt-okunur raporlama
  katmanı** — dispatch/simülasyon mantığını *bilinçli olarak* etkilemiyor (mevcut, dinamik
  doğrulamayla iki kez hata bulunmuş dispatch mantığına dokunmanın riskini almadık). Yeni
  `GET /api/v1/personnel?city=&district=&unit_id=` (o an görevde olan vardiya işaretli).
- **Rol hiyerarşisi genişledi** (`app/modules/auth/models.py`): `USER_ROLES` artık
  `admin | city_operator | ilce_amiri | merkez`. `ilce_amiri` (`users.district` yeni kolon)
  `city_operator`'ın ilçe düzeyine indirgenmiş hali; `merkez` tüm illeri GÖRÜR ama **salt-okunur**
  (`require_write_access` dışında tutuluyor). `app/core/auth.py > scope_district_for` yeni —
  `_units_payload` (REST+WS), `/geojson`, `/incidents/queue` bu filtreyi uyguluyor.
  **Bilinçli sınırlama:** geri kalan analitik uçları (trends/corridors/predictive/vb.) hâlâ
  yalnızca il düzeyinde kısıtlı, ilçe düzeyine indirilmedi — düşük risk/düşük öncelik (bkz. Yol
  Haritası). 2 yeni demo hesap: `merzifon_amirlik` (ilçe_amiri, Amasya/Merzifon), `merkez`.
- **Audit log** (`app/modules/audit/`): yeni `audit_log` tablosu + `log_audit()` — ihbar girişi,
  olay kapatma, birim/personel reseed, veri temizleme, girişlerin hepsi kayıt altında (kim/ne
  zaman/hangi il). `GET /api/v1/audit-log` (admin), admin panelinde kapalı `<details>` paneli.
  Dış entegrasyon gerektirmiyor — KVKK'ya hazırlık amaçlı, gerçek bir saklama/silme politikası
  henüz yok (bilinçli sınırlama, yol haritasında).
- **Eskalasyon paneli** (`app/modules/c4i/escalation.py > compute_escalations`, saf fonksiyon):
  20 dk'dan uzun süredir çözülmemiş VEYA çoklu-birim gerektirip 10 dk'dan uzun süredir eksik
  atanmış kritik olayları işaretler. `GET /api/v1/analytics/escalations`. Harita sidebar'ında
  ve admin panelinde "Eskalasyonlar" paneli (gerçek SMS/push kanalı yok — bilinçli olarak
  in-app uyarı panosu, Telegram'ın v2.6'da kaldırılmasıyla aynı ruhta).
- **Sentetik çok-yıllık geçmiş veri üreticisi** (`scripts/generate_synthetic_history.py`):
  `seasonal.py`'nin "gerçek mevsimsellik için birden fazla yılın verisi gerekir" notunu test
  etmek için — mevsimsel ağırlıklı (`kapkaç` yaz artışı, `gasp` kış artışı, `hırsızlık` düz
  kontrol grubu), `source="synthetic_history"` etiketli, tüm zaman damgaları ≥60 gün öncesi
  (aktif sevk/7-30 günlük pencereleri ETKİLEMEZ) ve `resolved_at` dolu üretilir. `--clear` ile
  tek komutla geri temizlenir — **canlı demo veritabanına kalıcı olarak bırakılmadı**,
  yalnızca doğrulama için bir kez çalıştırılıp temizlendi (bkz. doğrulama notu aşağıda).
- **Saha ekibi mobil görünümü** (`GET /field`, `app/ui/field.py`): tek sütun, büyük dokunma
  hedefli, mevcut `/personnel` + `/incidents/queue` + `/incidents/{id}/resolve` uçlarını tekrar
  kullanan bir ön-tasarım — gerçek bir mobil istemci değil, "gerçek istemcinin sözleşmesi böyle
  olabilir" gösterimi. Harita ve admin panelinden bağlantı eklendi.
- 13 yeni test (88→101): `current_shift`, `compute_escalations`, rol/scope fonksiyonları
  (`tests/test_auth.py`, yeni dosya) — `require_write_access`'in `merkez`'i reddettiği dahil.
- **Bu fazın kapsamı dışında (bilinçli):** personel için gerçek kimlik doğrulama/rozet sistemi,
  audit log saklama politikası, ilçe düzeyi kısıtlamanın tüm analitik uçlarına yayılması, gerçek
  SMS/push bildirim kanalı — hepsi yol haritasında.

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
| `app/modules/c4i/models.py` | `police_units` (+ `district`, `unit_type` sözlüğü), `police_unit_history` (iz sürme), `Personnel`/`SHIFTS` (personel/vardiya) |
| `app/modules/c4i/escalation.py` | Uzun süredir çözülmemiş/eksik-birim kritik olay tespiti (saf fonksiyon, `/analytics/escalations`) |
| `app/modules/audit/` | `audit_log` tablosu + `log_audit()` — yazma işlemlerinin denetim kaydı (`/audit-log`, admin) |
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
| `app/modules/auth/` | `users` tablosu (+ `district`), PBKDF2 hash + imzalı token (`security.py`), roller: `admin\|city_operator\|ilce_amiri\|merkez`, `/api/v1/auth/login`, demo hesap seed |
| `app/scrapers/ibb_ingestor.py` | İBB CKAN trafik duyuru ingestor'u |
| `alembic/` | Şema migrasyonları (baseline + dispatch/arrival/performans/district/users/çoklu-birim alanları uygulandı) |
| `frontend/static/geo/turkey-il.geojson` | 81 il sınırı (OSM, sadeleştirilmiş, ~225 KB) |
| `frontend/static/geo/turkey-ilce.geojson` | 928 ilçe sınırı (OSM admin-level-6, sadeleştirilmiş, ~1.27 MB) |
| `frontend/static/js/c4i.js` | Devriye katmanı (WS+polling), il/ilçe choropleth, bölge+birim-tipi filtresi, auth widget, trend/koridor/prediktif/performans/kapsama panelleri |
| `app/ui/admin.py` | Admin panel — sevk kuyruğu kartı, İBB tetikleme butonu, ihbar giriş formu, auth widget |
| `app/ui/login.py` | `/login` sayfası |
| `app/ui/field.py` | `/field` — saha ekibi mobil görünümü (personel/vardiya + sevk kuyruğu, mevcut uçları tekrar kullanır) |
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
| `generate_synthetic_history.py` | Mevsimsel ağırlıklı, `source="synthetic_history"` etiketli çok-yıllık sentetik geçmiş veri üretir/temizler (`--years`/`--clear`) — `seasonal.py`'yi test etmek için |

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
9. [x] ~~Personel/vardiya modeli~~ — v2.9'da yapıldı (salt-okunur roster, dispatch'i etkilemiyor)
10. [x] ~~Rol hiyerarşisi derinleştirme (ilçe_amiri + merkez)~~ — v2.9'da yapıldı
11. [x] ~~Audit log~~ — v2.9'da yapıldı (saklama politikası hâlâ eksik, madde 15)
12. [x] ~~Eskalasyon/bildirim paneli~~ — v2.9'da yapıldı (in-app, gerçek SMS/push değil)
13. [x] ~~Sentetik çok-yıllı geçmiş veri üretici~~ — v2.9'da yapıldı (`scripts/generate_synthetic_history.py`)
14. [x] ~~Saha ekibi mobil görünümü~~ — v2.9'da yapıldı (`/field`, gerçek mobil istemci değil)
15. [ ] Audit log saklama/silme politikası (KVKK) — şu an sınırsız birikiyor
16. [ ] `ilce_amiri` kısıtlamasını kalan analitik uçlarına (trends/corridors/predictive/seasonal/
        scorecard) da yay — şu an yalnızca `/units`, `/geojson`, `/incidents/queue` ilçe filtreli
17. [ ] Personel icin gercek kimlik dogrulama/rozet sistemi (su an sadece roster verisi, giris
        kimligiyle iliskili degil)
18. [ ] Eskalasyon panelinde gercek bildirim kanali (SMS/push) — su an yalnizca in-app panel

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

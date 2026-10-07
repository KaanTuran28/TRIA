# TRIA C4I — Çok Şehirli Asayiş Platformu Planı

> **Durum:** Taslak plan, onay bekliyor. Kod değişikliği henüz yapılmadı.
> **Bağlam (2026-07-13):** TRIA, Türkiye'deki
> il/ilçe asayiş yönetimlerinin kullanacağı gerçek bir platform olarak geliştiriliyor.
> Gerçek operasyonel veri (ihbar, birim GPS'i vb.) entegrasyonu ileride ilgili kurumlar
> tarafından yapılacak — **bizim işimiz sistemin mantığını ve mimarisini ikna edici şekilde
> göstermek.** Bu yüzden bu fazda auth/production-hardening değil, **doğru veri modeli +
> gerçekçi senaryo + akıcı UX** önceliklidir.

## 1. Hedef Senaryo (referans örnek: Amasya → Merzifon)

Bir ilin asayiş yönetimi platforma girdiğinde:
1. Kendi ilini (Amasya) ve istediği ilçesini (Merzifon) seçer / filtreler.
2. O bölgedeki **tüm devriye birimlerini türüne göre** haritada görür: asayiş, trafik,
   TEM (terör), Yunus (motorize hızlı müdahale), çevik kuvvet, narkotik vb. — her birimin
   anlık konumu bellidir.
3. Yeni bir ihbar geldiğinde (çağrı merkezi / vatandaş bildirimi) **anında** haritada aktif
   olay olarak belirir — dispatch akışı zaten mevcut (v2.3), burada eksik olan "haber
   kazıma" değil, **doğrudan ihbar girişi** kanalıdır.
4. Mahalle/ilçe bazlı suç istatistiklerini görür: hangi suç türü nerede yoğun, trafik
   kazaları hangi noktalarda kümeleniyor.
5. Bu görünüm il/ilçe bazlı **filtrelenebilir** olduğu için her şehir kendi verisine
   odaklanabilir — aynı platformu 81 il de kullanabilir.

Bu, mevcut mimarinin (police_units + crime_events + dispatch + choropleth) üzerine inşa
edilecek; sıfırdan yeni bir sistem değil, **coğrafi hiyerarşi + filtreleme + gerçek zamanlı
ihbar girişi** katmanları ekleniyor.

## 2. Mimari Yaklaşım

- **Tek veritabanı, mantıksal şehir/ilçe ayrımı.** Ayrı tenant/DB şeması gerekmiyor —
  `city`/`district` kolonlarıyla filtreleme yeterli (81 il için de ölçeklenir). Gerçek
  kurumsal devreye alma aşamasında (bu fazın kapsamı dışında) şehir bazlı kullanıcı/rol
  sistemi eklenebilir — bkz. §7 Gelecek Çalışmalar.
- **`police_units` zaten `city` ve `unit_type` alanlarına sahip** (`app/modules/c4i/models.py`).
  Eksik olan: `district` (ilçe) kolonu ve `unit_type` sözlüğünün asayiş biriminin gerçek
  türlerini yansıtacak şekilde genişletilmesi.
- **`crime_events` şu an sadece `city` biliyor, `district`/`mahalle` bilmiyor** — bu, mahalle
  bazlı analiz için en kritik eksik.
- **Mahalle poligon verisi konusunda gerçekçi olmak lazım:** Araştırdım — Türkiye genelinde
  ücretsiz/açık mahalle *sınır* poligonu (32 bin+ mahalle) kısıtlı: `izzetkalic/geojsons-of-turkey`
  yalnızca İstanbul mahallelerini içeriyor; HDX/geoBoundaries genelde il-ilçe (ADM1-ADM2)
  seviyesinde duruyor; tam Türkiye mahalle poligonu ücretli kaynaklarda mevcut (Geolocet,
  Başarsoft). Bu yüzden mahalle desteğini **iki aşamalı** öneriyorum:
  - **Yakın vade:** İlçe bazlı poligon (zaten yol haritasında vardı, ücretsiz kaynak mevcut)
    + mahalle **adını** nokta/merkez bazlı yaklaşık eşleştirme (poligon değil, "en yakın
    mahalle merkezi" mantığı) — demo ve gerçek kullanım için yeterince ikna edici.
  - **İleri vade:** Gerçek mahalle poligon kaynağı bulunursa (ücretli veya kurumdan temin
    edilirse) tam choropleth'e geçiş.

Kaynaklar (mahalle/ilçe sınırları):
- [izzetkalic/geojsons-of-turkey](https://github.com/izzetkalic/geojsons-of-turkey) — il/ilçe zaten kullanılıyor, İstanbul mahalle
- [Geolocet — Turkey Neighbourhoods (Mahalleler) Boundaries](https://geolocet.com/products/turkey-admin-level-8-neighbourhoods-and-unincorporated-villages) — ücretli, tüm Türkiye
- [Başarsoft — İl-İlçe-Mahalle Sınırları](https://www.basarsoft.com.tr/en/provincial-district-neighborhood-boundaries/) — ücretli, tüm Türkiye
- [HDX — Türkiye Subnational Administrative Boundaries](https://data.humdata.org/dataset/cod-ab-tur) — genelde ADM2 (ilçe) seviyesinde

## 3. Fazlar

### Faz 1 — Coğrafi hiyerarşi + birim tipi genişletmesi
- `police_units.district` (String, nullable, index) eklenir — Alembic migration.
- `crime_events.district` (String, nullable, index) eklenir — ingestion sırasında ilçe
  poligonuna point-in-polygon ile atanır (choropleth'teki il eşleştirme mantığının aynısı,
  ilçe seviyesine indirgenmiş hali).
- `unit_type` sözlüğü genişletilir: `asayis | trafik | tem | yunus | cevik_kuvvet | narkotik | kom`
  (kod tarafında sabit liste + frontend'de ikon/renk eşlemesi).
- `seed_police_units()` güncellenir: örnek il/ilçe (Amasya/Merzifon dahil) için karışık
  birim tipleriyle gerçekçi tohum veri üretir.

### Faz 2 — Gerçek zamanlı ihbar girişi + aktif olay katmanı
- Yeni uç nokta: `POST /api/v1/incidents/report` — dispatcher/çağrı merkezi girişi
  (kategori, konum, şiddet, açıklama, il/ilçe) → doğrudan `crime_events` satırı oluşturur
  (`source="manual_ihbar"`), mevcut dispatch kuyruğuna otomatik girer (v2.3 akışı zaten
  destekliyor).
- Mevcut `/ws/units` yayınına ek olarak (ya da aynı kanaldan) yeni/aktif olaylar anlık
  push edilir — frontend haritada **aktif olay pin'i** olarak beliriyor (şu an choropleth
  var ama tekil "aktif olay" katmanı yok, bu eksik netleşti).
- Admin panelde basit "Yeni İhbar Gir" formu (simülasyon/demo amaçlı çağrı merkezi girişi).

### Faz 3 — Filtreleme UI (il → ilçe → birim tipi)
- Harita üstünde il/ilçe seçici (cascading dropdown) + birim tipi çoklu seçim (checkbox).
- Seçime göre `/units`, `/geojson`, `/analytics/*` çağrılarına `city`/`district`/`unit_type`
  query parametreleri eklenir (backend filtre desteği + frontend state).

### Faz 4 — Mahalle/ilçe bazlı suç ve trafik analitiği
- `GET /api/v1/analytics/crime-types?city=&district=` — suç türü dağılımı, bölge bazlı.
- `GET /api/v1/analytics/traffic-hotspots?city=&district=` — trafik kazası yoğunluk noktaları
  (mevcut `corridors` mantığının `incident_type=traffic_accident` filtresiyle uzantısı).
- Sidebar'da yeni paneller: "Suç Türü Dağılımı" (bar/donut), "Trafik Yoğunluk Noktaları".

### Faz 5 — İlçe bazlı choropleth (yol haritasında zaten vardı, bu planla birleşiyor)
- `frontend/static/geo/turkey-ilce.geojson` (admin-level-6 kaynağından, aynı simplify
  yaklaşımıyla) + `renderRiskChoropleth` ilçe seviyesine genelleştirilir (il seçilince
  ilçelere "zoom" / drill-down).

## 4. Test Stratejisi

- Yeni saf fonksiyonlar (`crime-types` / `traffic-hotspots` aggregation) DB'den bağımsız
  test edilir — mevcut `performance.py`/`coverage.py` desenine paralel.
- Yeni endpoint'ler için contract testleri (filtre parametreleri, boş/geçersiz il-ilçe).
- Mevcut 65 test kırılmadan geçmeli; migration sonrası `python run.py migrate` + smoke test.

## 5. Bu Fazın Kapsamı DIŞINDA (bilinçli olarak ertelendi)

- Gerçek kullanıcı auth / rol bazlı erişim (şehir bazlı giriş) — gerçek kurumlar devreye
  girmeden önce gerekmiyor, şimdilik tüm filtreler herkese açık demo mantığında.
- Gerçek AVL/GPS entegrasyonu — devriye hareketi hâlâ simülasyon, sözleşme (API şekli)
  gerçek beslemeyle uyumlu tasarlanmaya devam ediyor.
- Tam Türkiye mahalle poligon choropleth'i — ücretli veri kaynağı gerektiriyor (§2).

## 6. Özet Değişiklik Listesi

| Katman | Değişiklik |
|---|---|
| DB | `police_units.district`, `crime_events.district` (+ Alembic migration) |
| Model | `unit_type` sözlüğü genişletilir (asayis/trafik/tem/yunus/cevik_kuvvet/narkotik/kom) |
| API | `POST /incidents/report`, `GET /analytics/crime-types`, `GET /analytics/traffic-hotspots`, mevcut endpoint'lere `district`/`unit_type` filtresi |
| Frontend | İl→ilçe seçici, birim tipi filtre, "Aktif Olaylar" pin katmanı, "Yeni İhbar Gir" formu, suç türü/trafik yoğunluk panelleri |
| Veri | İlçe geojson (`turkey-ilce.geojson`), mahalle nokta-bazlı yaklaşık eşleştirme |

## 7. Gelecek Çalışmalar (bu faz bittikten sonra)

1. Şehir bazlı kullanıcı hesabı + rol yetkilendirme (gerçek kurumlar platforma girdiğinde) —
   şu an admin panelinde hiç auth yok, bu noktada kritikleşir.
2. Tam mahalle poligon kaynağı temin edilirse (ücretli/kurumsal) tam choropleth'e geçiş.
3. Gerçek ihbar/çağrı merkezi entegrasyonu (152/155 gibi resmi sistemlerle API köprüsü) —
   kurumun kendi işi, bizim tarafımızda sadece giriş sözleşmesi hazır olmalı.
4. Çoklu-birim sevk (bir olaya birden fazla ekip ataması — mevcut yol haritası madde 5).
5. `police_unit_history` üzerinden ısı haritası / yoğunluk analizi (iz verisi birikince).
6. WS için tek yayıncı (broadcast) mimarisi — çok şehirli kullanımda istemci sayısı artınca
   önem kazanır (mevcut yol haritası madde 3).
7. "Akıllı şehir güvenlik statüsü" vizyonu için: platformun sağladığı somut KPI'ları
   (müdahale süresi, kapsama boşluğu, suç trendi) her il için karşılaştırmalı bir
   "puan kartı" haline getirmek — pazarlama/kurumsal sunum değeri yüksek.

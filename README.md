# TRİA — Türkiye Risk Intelligence Network

![Python](https://img.shields.io/badge/python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-async-009688)
![PostGIS](https://img.shields.io/badge/PostgreSQL-PostGIS-336791)
![Tests](https://img.shields.io/badge/tests-101-brightgreen)
![License](https://img.shields.io/badge/license-MIT-green)

<p align="center"><b><a href="#english">English</a></b> · <b><a href="#türkçe">Türkçe</a></b></p>

---

## English

TRİA is an OSINT + GIS platform for public-safety incidents in Turkey. It collects news about crime, police operations, traffic accidents and public-order events from open sources, structures them with an LLM, stores them in PostGIS and shows them on a live map. On top of that it runs a C4I (command & control) simulation with patrol units, dispatch, analytics and role-based access for all 81 provinces.

It started as my undergraduate graduation project and grew into a multi-city public-safety prototype.

> **Status:** prototype. Patrol movement, personnel and shifts are **simulated** — there is no real AVL/GPS, 112/155 call-centre or SMS integration. The API contracts are designed so that real feeds could replace the simulation later.

### Data pipeline

![TRİA data pipeline](Görseller/Şema.png)

1. **Sources** (`config/sources.json`): GDELT GKG GeoJSON, RSS feeds (cloudscraper + feedparser), public Telegram channels (`t.me/s/...`) and Istanbul Metropolitan Municipality (İBB) open traffic data.
2. **Pre-filter:** keyword rules keep crime and public-order news and drop disasters, weather and similar noise before any LLM call.
3. **Deduplication:** URL check plus Jaccard similarity on titles.
4. **Analysis:**
   - *Standard track:* raw text goes to a Groq LLM (default `llama-3.1-8b-instant`), which returns the incident type, location and a 1–10 severity score.
   - *Fast track:* sources that already have coordinates (GDELT) skip the LLM.
5. **Spatial validation:** geocoding, foreign-place filtering and a Turkey bounding-box check. The district is filled automatically with a point-in-polygon lookup against 928 district boundaries (shapely).
6. **Storage:** PostgreSQL/PostGIS (`crime_events`).

### Features

**Map (Leaflet.js)**
- Live incident markers with clustering and a heatmap layer.
- Province and district choropleth normalised per 100,000 people (TÜİK 2025 population data).
- Region and unit-type filters, dark theme and a mobile layout.

**C4I simulation**
- 173 patrol units seeded across all 81 provinces in proportion to population, in five types: public order, traffic, counter-terrorism, motorcycle (Yunus) and riot police.
- Movement engine with patrol, en-route and on-scene modes (3-second tick), streamed to the map over WebSocket.
- Dispatch: priority queue, haversine distance and ETA, and multi-unit dispatch that prefers a different unit type for the second unit.
- Personnel and day/night shift model, plus an escalation panel for critical incidents that stay unresolved or under-staffed for too long.

**Analytics**
- Response-time KPIs: dispatch delay, travel time, time on scene and total response time.
- Coverage-gap score using where units actually were at the time of each incident.
- Transparent rule-based early-warning score. It is a formula, not an ML model.
- Province-by-province risk scorecard and seasonal (monthly) analysis.

**Access control and auditing**
- Users with PBKDF2 password hashing and signed tokens.
- Roles: `admin`, `city_operator` (one province), `ilce_amiri` (one district) and `merkez` (all provinces, read-only). Data is filtered on the server according to the role.
- Every write action (incident report, closing an incident, reseeding, login and so on) is written to an audit log.

**Interfaces:** map (`/map`), admin panel (`/admin`), mobile field-team view (`/field`), login (`/login`) and Swagger docs (`/api/docs`).

### Tech stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (async), SQLAlchemy 2 + asyncpg, APScheduler, Alembic |
| Database | PostgreSQL 15 + PostGIS 3.4 (GeoAlchemy2) |
| AI | Groq API (Llama 3.1 8B) |
| Spatial | shapely, OSM province/district GeoJSON |
| Frontend | Leaflet.js, vanilla JavaScript |
| Deployment | Docker, Docker Compose |
| Tests | pytest, pytest-asyncio, httpx — 101 tests |

### Getting started

Requirements: Docker Desktop. To run outside Docker you also need Python 3.12.

1. Create a `.env` file in the project root:

   ```env
   DATABASE_URL=postgresql+asyncpg://postgres:postgres@database:5432/tria_db
   GROQ_API_KEY=your_groq_key
   ADMIN_API_KEY=change_me
   AUTH_SECRET_KEY=change_me
   ```

   Optional: `GROQ_MODEL`, `RUN_SCAN_ON_STARTUP`, `MAX_ARTICLE_AGE_HOURS`, and `DEMO_*_PASSWORD` to override the demo account passwords.

2. Start the stack:

   ```bash
   python run.py            # builds and starts the database and app with Docker Compose
   python run.py migrate    # applies Alembic migrations
   ```

3. Open `http://localhost:8000/map`. Use `/admin` to trigger a scan (`POST /scrape`) or the İBB import.

Other commands: `python run.py restart` rebuilds the app after code changes, and `python run.py local` runs uvicorn locally while the database stays in Docker.

**Demo accounts:** `admin`, `amasya_asayis`, `istanbul_asayis`, `merzifon_amirlik` and `merkez`. Their default passwords are in `app/modules/auth/seed.py`. Change them through `.env` before exposing the app anywhere.

### Tests

```bash
pip install -r requirements-dev.txt
pytest
```

The `scripts/` folder holds manual tools that are not part of the test suite: a smoke test, source diagnostics, a Telegram channel probe and a synthetic history generator.

### Project structure

```
TRIA/
├── main.py / run.py          # App entry point and Docker/uvicorn/migration helper
├── app/
│   ├── core/                 # Database, auth helpers, logging
│   ├── modules/
│   │   ├── crime/            # OSINT pipeline, geolocation, spatial search
│   │   ├── c4i/              # Units, simulation, dispatch, analytics
│   │   ├── auth/             # Users, roles, tokens
│   │   └── audit/            # Audit log
│   ├── scrapers/             # İBB, API and Telegram ingestors
│   ├── services/             # Groq LLM analyser
│   └── ui/                   # Admin, login and field pages
├── frontend/                 # Map template, JS, CSS, province/district GeoJSON
├── alembic/                  # Database migrations
├── config/sources.json       # Data source definitions
├── docs/                     # Graduation report, plans, data source notes
├── scripts/                  # CLI diagnostic tools
└── tests/                    # pytest suite
```

### Known limitations

- Patrol movement, personnel and shifts are simulated.
- `ADMIN_API_KEY` still works as a system-wide master key for backward compatibility. It should be removed before any real deployment.
- There is no retention or deletion policy for the audit log yet.
- Choropleths go down to district level. There is no neighbourhood level because no free data source was found.
- Never commit `.env`, because it holds the Groq API key.

### License

MIT — see [LICENSE](./LICENSE).

---

## Türkçe

TRİA, Türkiye'deki asayiş olayları için bir OSINT + CBS platformudur. Suç, polis operasyonu, trafik kazası ve kamu düzeni haberlerini açık kaynaklardan toplar, bir büyük dil modeliyle yapılandırır, PostGIS'te saklar ve canlı bir haritada gösterir. Bunun üzerine 81 il için devriye birimleri, sevk, analitik ve rol bazlı erişim içeren bir C4I (komuta-kontrol) simülasyonu çalıştırır.

Lisans bitirme projem olarak başladı, sonra çok şehirli bir asayiş prototipine dönüştü.

> **Durum:** prototip. Devriye hareketi, personel ve vardiyalar **simülasyondur**; gerçek AVL/GPS, 112/155 çağrı merkezi veya SMS entegrasyonu yoktur. API sözleşmeleri, ileride simülasyonun yerine gerçek beslemelerin geçebileceği şekilde tasarlandı.

### Veri boru hattı

![TRİA veri boru hattı](Görseller/Şema.png)

1. **Kaynaklar** (`config/sources.json`): GDELT GKG GeoJSON, RSS beslemeleri (cloudscraper + feedparser), herkese açık Telegram kanalları (`t.me/s/...`) ve İBB açık trafik verisi.
2. **Ön filtre:** anahtar kelime kuralları, LLM'e gitmeden önce suç ve asayiş haberlerini tutar; afet, hava durumu gibi gürültüyü atar.
3. **Tekilleştirme:** URL kontrolü ve başlıklarda Jaccard benzerliği.
4. **Analiz:**
   - *Standart hat:* ham metin Groq LLM'e gider (varsayılan `llama-3.1-8b-instant`). Model olay türünü, konumu ve 1–10 arası bir şiddet puanını döndürür.
   - *Hızlı hat:* koordinatı zaten olan kaynaklar (GDELT) LLM'i atlar.
5. **Mekânsal doğrulama:** geokodlama, yurt dışı yer adı filtresi ve Türkiye sınır kutusu kontrolü. İlçe, 928 ilçe sınırı üzerinde nokta-çokgen sorgusuyla otomatik doldurulur (shapely).
6. **Depolama:** PostgreSQL/PostGIS (`crime_events`).

### Özellikler

**Harita (Leaflet.js)**
- Kümelenen canlı olay işaretleri ve ısı haritası katmanı.
- 100 bin kişi başına normalleştirilmiş il ve ilçe renk haritası (TÜİK 2025 nüfus verisi).
- Bölge ve birim türü filtreleri, koyu tema ve mobil düzen.

**C4I simülasyonu**
- 81 ile nüfusa orantılı dağıtılmış 173 devriye birimi, beş türde: asayiş, trafik, TEM, Yunus ve çevik kuvvet.
- Devriye, olaya gidiş ve olay yerinde modlarıyla hareket motoru (3 saniyelik döngü); konumlar haritaya WebSocket ile anlık gelir.
- Sevk: öncelik kuyruğu, haversine mesafe ve varış süresi tahmini. Çoklu birim gerektiğinde ikinci birim için farklı türde bir birim tercih edilir.
- Personel ve gündüz/gece vardiya modeli. Uzun süredir çözülmeyen veya eksik birimli kritik olaylar için eskalasyon paneli.

**Analitik**
- Müdahale süresi göstergeleri: sevk gecikmesi, yol süresi, olay yerinde geçen süre ve toplam müdahale süresi.
- Olay anında birimlerin gerçekte nerede olduğunu kullanan kapsama boşluğu skoru.
- Şeffaf, kural tabanlı erken uyarı skoru. Bir makine öğrenmesi modeli değil, bir formüldür.
- İller arası risk karnesi ve aylık (mevsimsel) analiz.

**Erişim kontrolü ve denetim**
- PBKDF2 ile hash'lenen şifreler ve imzalı token'larla kullanıcı sistemi.
- Roller: `admin`, `city_operator` (tek il), `ilce_amiri` (tek ilçe) ve `merkez` (tüm iller, salt okunur). Veriler role göre sunucu tarafında filtrelenir.
- Her yazma işlemi (ihbar girişi, olay kapatma, yeniden tohumlama, giriş vb.) denetim kaydına (audit log) yazılır.

**Arayüzler:** harita (`/map`), yönetim paneli (`/admin`), mobil saha ekibi görünümü (`/field`), giriş (`/login`) ve Swagger belgeleri (`/api/docs`).

### Kullanılan teknolojiler

| Katman | Teknoloji |
|---|---|
| Backend | FastAPI (async), SQLAlchemy 2 + asyncpg, APScheduler, Alembic |
| Veritabanı | PostgreSQL 15 + PostGIS 3.4 (GeoAlchemy2) |
| Yapay zekâ | Groq API (Llama 3.1 8B) |
| Mekânsal | shapely, OSM il/ilçe GeoJSON |
| Frontend | Leaflet.js, vanilla JavaScript |
| Dağıtım | Docker, Docker Compose |
| Test | pytest, pytest-asyncio, httpx — 101 test |

### Kurulum

Gereksinim: Docker Desktop. Docker dışında çalıştırmak için ayrıca Python 3.12 gerekir.

1. Proje kökünde bir `.env` dosyası oluşturun:

   ```env
   DATABASE_URL=postgresql+asyncpg://postgres:postgres@database:5432/tria_db
   GROQ_API_KEY=groq_anahtariniz
   ADMIN_API_KEY=degistirin
   AUTH_SECRET_KEY=degistirin
   ```

   İsteğe bağlı: `GROQ_MODEL`, `RUN_SCAN_ON_STARTUP`, `MAX_ARTICLE_AGE_HOURS` ve demo hesap şifrelerini değiştirmek için `DEMO_*_PASSWORD`.

2. Sistemi başlatın:

   ```bash
   python run.py            # veritabanını ve uygulamayı Docker Compose ile derleyip başlatır
   python run.py migrate    # Alembic migration'larını uygular
   ```

3. `http://localhost:8000/map` adresini açın. Tarama (`POST /scrape`) veya İBB verisi aktarımı için `/admin` panelini kullanın.

Diğer komutlar: `python run.py restart` kod değişikliğinden sonra uygulamayı yeniden derler, `python run.py local` ise veritabanı Docker'da kalırken uvicorn'u yerelde çalıştırır.

**Demo hesaplar:** `admin`, `amasya_asayis`, `istanbul_asayis`, `merzifon_amirlik` ve `merkez`. Varsayılan şifreleri `app/modules/auth/seed.py` dosyasındadır. Uygulamayı herhangi bir yerde yayına açmadan önce `.env` üzerinden değiştirin.

### Testler

```bash
pip install -r requirements-dev.txt
pytest
```

`scripts/` klasöründe test paketine dahil olmayan elle çalıştırılan araçlar var: hızlı sağlık testi, kaynak teşhisi, Telegram kanal taraması ve sentetik geçmiş veri üretici.

### Proje yapısı

```
TRIA/
├── main.py / run.py          # Uygulama girişi ve Docker/uvicorn/migration yardımcısı
├── app/
│   ├── core/                 # Veritabanı, yetki yardımcıları, loglama
│   ├── modules/
│   │   ├── crime/            # OSINT boru hattı, konumlama, mekânsal arama
│   │   ├── c4i/              # Birimler, simülasyon, sevk, analitik
│   │   ├── auth/             # Kullanıcılar, roller, token'lar
│   │   └── audit/            # Denetim kaydı
│   ├── scrapers/             # İBB, API ve Telegram veri alıcıları
│   ├── services/             # Groq LLM analizcisi
│   └── ui/                   # Yönetim, giriş ve saha sayfaları
├── frontend/                 # Harita şablonu, JS, CSS, il/ilçe GeoJSON
├── alembic/                  # Veritabanı migration'ları
├── config/sources.json       # Veri kaynağı tanımları
├── docs/                     # Bitirme raporu, planlar, veri kaynağı notları
├── scripts/                  # Komut satırı teşhis araçları
└── tests/                    # pytest test paketi
```

### Bilinen kısıtlar

- Devriye hareketi, personel ve vardiyalar simülasyondur.
- `ADMIN_API_KEY` geriye dönük uyumluluk için hâlâ sistem genelinde bir ana anahtar gibi çalışıyor. Gerçek bir kullanımdan önce kaldırılmalı.
- Denetim kaydı için henüz bir saklama/silme politikası yok.
- Renk haritaları ilçe düzeyine kadar iniyor. Ücretsiz veri kaynağı bulunamadığı için mahalle düzeyi yok.
- `.env` dosyasını asla commit etmeyin, içinde Groq API anahtarı bulunur.

### Lisans

MIT — bkz. [LICENSE](./LICENSE).

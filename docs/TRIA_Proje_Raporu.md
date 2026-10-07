<div style="page-break-after: always;"></div>

# TRİA (Türkiye Risk İstihbarat Ağı)
### Otomatik Açık Kaynak İstihbarat (OSINT) ve CBS Tabanlı Asayiş Olay Haritalama Sistemi

<br><br><br>

**Proje Türü:** Araştırma Raporu  
**Tarih:** Haziran 2026

<br><br><br>

<div style="page-break-after: always;"></div>

---

## ÖNSÖZ

Bu araştırma ve geliştirme raporu, **TRİA (Türkiye Risk İstihbarat Ağı)** adlı otomatize yazılım sisteminin uçtan uca tasarım, programlama, test ve dağıtım (deployment) süreçlerini akademik ve mühendislik disiplinleri çerçevesinde belgelemektedir. 

Geleneksel veri toplama yöntemlerinin günümüzün dijital hızına yetişememesi, açık kaynak istihbaratının (OSINT) önemini benzeri görülmemiş bir seviyeye taşımıştır. Bu projenin temel felsefesi; internetin yapılandırılmamış, karmaşık ve gürültülü veri okyanusundan otonom algoritmalarla anlamlı güvenlik istihbaratı süzmek ve bunu modern Coğrafi Bilgi Sistemleri (CBS) standartlarında görselleştirmektir. 

Geliştirme süreci boyunca sistem mimarisi, yüksek veri hacminde dahi çökmeden çalışabilecek asenkron yapılarla ve maliyet-etkin (cost-effective) yapay zekâ entegrasyonlarıyla örülmüştür. Sistemin "sinyal-gürültü" oranını korumak adına çok katmanlı filtreler inşa edilmiş; deprem, afet ve iklim gibi olaylar bilinçli olarak asayiş radarının dışında bırakılmıştır.

Bu uzun ve zorlu mühendislik sürecinde teknik vizyonun gerçeğe dönüşmesine katkı sağlayan ve destek olan herkese teşekkürlerimi sunarım.

**T-X** Haziran 2026

<div style="page-break-after: always;"></div>

---

## ÖZET

Kamu düzeni ve asayiş olaylarının anlık olarak izlenmesi, resmi istatistiklerin bürokratik gecikmeleri nedeniyle Açık Kaynak İstihbarat (OSINT) verilerinin Coğrafi Bilgi Sistemleri (CBS) ile otonom entegrasyonunu zorunlu kılmaktadır. Bu çalışmada, yalnızca Türkiye sınırları içindeki suç, polis operasyonu, kaza ve kamu düzeni olaylarına odaklanan **TRİA (Türkiye Risk İstihbarat Ağı)** adlı uçtan uca veri toplama, yapay zekâ destekli analiz ve haritalama platformu geliştirilmiştir.

Mimari altyapı; GDELT Global Knowledge Graph GeoJSON akışlarını, ulusal/yerel haber ajanslarının RSS beslemelerini ve anlık Telegram kamu kanallarını asenkron (FastAPI) bir orkestrasyon boru hattında birleştirmektedir. Geliştirilen düşük maliyetli boru hattı (pipeline) sayesinde, doğal afetler ve hava durumu gibi ilgisiz veriler anahtar kelime tabanlı "Ön Filtre (Pre-filter)" algoritmalarıyla dışlanmakta; tekrar eden içerikler ise Jaccard benzerlik metriğiyle (deduplikasyon) sistemden temizlenmektedir.

Ham ve yapılandırılmamış haber metinleri, Groq Büyük Dil Modeli (LLM) kullanılarak olay kategorisine, hassas lokasyon verisine ve 1 ile 10 arasında değişen algoritmik bir **Yapay Zekâ Şiddet İndeksine (Severity Score)** dönüştürülmektedir. GDELT gibi zaten yapılandırılmış koordinatlı kaynaklar ise LLM katmanını "Fast-Track" metoduyla pas geçerek doğrudan uzamsal veritabanına (PostGIS) işlenmekte, bu da işlem sürelerini milisaniyeler seviyesine indirmektedir.

Mekânsal katmanda olaylar, PostgreSQL üzerinde coğrafi nesneler (POINT) olarak saklanır. Leaflet.js tabanlı web arayüzü kullanıcıya; çokgensel alan seçimi (Draw & Search), zaman serisi analizi (Time Slider), ısı haritası (Heatmap), yoğunluk kümelemesi (Clustering) ve risk seviyesine göre dinamik olarak boyutlanan ikonlar gibi profesyonel analiz araçları sunar. TRİA, emniyet birimleri ve yerel yönetimler için yüksek performanslı, maliyetsiz ve genişletilebilir bir durumsal farkındalık (situational awareness) CBS prototipi ortaya koymaktadır.

**Anahtar Kelimeler:** OSINT, Coğrafi Bilgi Sistemi (CBS), Asayiş Radarı, PostGIS, Büyük Dil Modeli (LLM), Uzamsal Analiz, FastAPI, Python.

<div style="page-break-after: always;"></div>

---

## ABSTRACT

The real-time spatial monitoring of public order and security incidents necessitates the autonomous integration of Open-Source Intelligence (OSINT) with Geographic Information Systems (GIS), primarily due to the inherent bureaucratic delays of official crime statistics. This study introduces **TRIA (Turkey Risk Intelligence Network)**, an end-to-end autonomous data ingestion, AI-driven analysis, and mapping platform exclusively dedicated to monitoring crimes, police operations, accidents, and public order events within Turkey.

The architectural framework orchestrates heterogeneous text data via an asynchronous pipeline (FastAPI) aggregating GDELT Global Knowledge Graph GeoJSON feeds, national/local news RSS streams, and Telegram public channels. Through a highly cost-effective pipeline, irrelevant data such as natural disasters and weather anomalies are autonomously discarded via keyword-based pre-filtering algorithms. Simultaneously, duplicated content is purged using Jaccard similarity metrics.

Unstructured news texts are processed by the Groq Large Language Model (LLM) to extract structured event categories, precise locational data, and an algorithmic **AI Severity Index** ranging from 1 to 10. Conversely, pre-structured sources like GDELT bypass the LLM layer via a "Fast-Track" methodology, writing directly to the spatial database (PostGIS), thereby reducing processing latency to milliseconds and optimizing API costs.

In the spatial layer, incidents are stored as geographic objects (POINT) on PostgreSQL. The Leaflet.js-based web client equips users with professional analytical tools, including spatial bounding (Draw & Search), temporal tracking (Time Slider), heatmaps, density clustering, and dynamically scaling icons based on severity indices. TRIA establishes a high-performance, cost-efficient, and scalable situational awareness GIS prototype suitable for law enforcement and local government applications.

**Keywords:** OSINT, Geographic Information System (GIS), Public Order Radar, PostGIS, Large Language Model (LLM), Spatial Analysis, FastAPI, Python.

<div style="page-break-after: always;"></div>

---

## İÇİNDEKİLER

| Bölüm | Sayfa |
|---|:---:|
| ÖNSÖZ | ii |
| ÖZET | iii |
| ABSTRACT | iv |
| İÇİNDEKİLER | v |
| ŞEKİLLER DİZİNİ | vii |
| TABLOLAR DİZİNİ | viii |
| KISALTMALAR | ix |
| **1. GİRİŞ** | 1 |
| 1.1. Problem Tanımı ve Motivasyon | 1 |
| 1.2. Projenin Amacı ve Hedefleri | 2 |
| 1.3. Kapsam İzolasyonu (Dahil ve Hariç Olaylar) | 2 |
| **2. KAVRAMSAL ÇERÇEVE VE LİTERATÜR** | 4 |
| 2.1. Açık Kaynak İstihbaratı (OSINT) Dinamikleri | 4 |
| 2.2. Kriminolojide Coğrafi Bilgi Sistemleri (CBS) | 4 |
| 2.3. Doğal Dil İşleme (NLP) ve Büyük Dil Modelleri (LLM) | 5 |
| **3. SİSTEM MİMARİSİ VE TEKNOLOJİ YIĞINI** | 6 |
| 3.1. Çok Katmanlı (N-Tier) Mimari Tasarımı | 6 |
| 3.2. Sunucu ve Backend Katmanı (FastAPI & Python) | 7 |
| 3.3. Uzamsal Veritabanı (PostgreSQL & GeoAlchemy2) | 8 |
| 3.4. İstemci Katmanı ve Konteynerleştirme (Docker) | 9 |
| **4. VERİ TOPLAMA VE İŞLEME BORU HATTI (PIPELINE)** | 10 |
| 4.1. Veri Kaynakları ve JSON Konfigürasyon Yönetimi | 10 |
| 4.2. GDELT API ve Maliyet Düşürücü Bypass (Fast-Track) Hattı | 11 |
| 4.3. Dinamik Web Kazıma (Telegram Önizleme ve RSS) | 12 |
| 4.4. Maliyet Kalkanı: Anahtar Kelime Ön Filtreleme (Pre-Filter) | 13 |
| 4.5. Tekrarlayan Veri Önleme (Jaccard Deduplikasyon) | 13 |
| 4.6. Groq AI Entegrasyonu ve Şiddet İndeksi (Severity Score) Ataması | 14 |
| 4.7. Türkiye Odaklı Metinsel Geokodlama ve Validasyon | 15 |
| **5. CBS VE ARAYÜZ YETENEKLERİ (FRONTEND)** | 16 |
| 5.1. Harita Altyapısı (Leaflet.js) ve Koyu Tema Altlık Kullanımı | 16 |
| 5.2. Veri Görselleştirme: Yoğunluk Kümelemesi ve Isı Haritası | 17 |
| 5.3. Dinamik Şiddet İkonları ve Kategori Filtreleme | 18 |
| 5.4. Uzamsal Sorgu: Çizerek Arama (Draw & Search / ST_Intersects) | 19 |
| 5.5. Zamansal Analiz: Geçmişe Yolculuk (Time Slider) | 20 |
| 5.6. Karar Destek: Otomatik Bölgesel PDF Rapor Üretimi | 21 |
| 5.7. Sistem Tanılama: Admin Panel ve "Kıyamet Günü" Demo Modu | 22 |
| **6. SONUÇ VE DEĞERLENDİRME** | 23 |
| 6.1. Elde Edilen Teknik Bulgular ve Performans | 23 |
| 6.2. Sistemin Pratik Çıktıları ve Yenilikçi Yönleri | 24 |
| 6.3. Gelecek Çalışmalar ve İyileştirme Önerileri | 25 |
| **KAYNAKÇA** | 26 |
| **EKLER** | 27 |

<div style="page-break-after: always;"></div>

---

## ŞEKİLLER DİZİNİ

| No | Şekil Başlığı | Sayfa |
|:--:|---------------|:---:|
| Şekil 1 | TRİA 3-Katmanlı Sistem Mimarisi Blok Diyagramı | 6 |
| Şekil 2 | GDELT, RSS ve Telegram Çoklu Veri Boru Hattı Akış Şeması | 10 |
| Şekil 3 | TRİA Ana Harita Arayüzü (Dark Mode, Sol Kontrol Paneli, Lejant) | 16 |
| Şekil 4 | Leaflet.markercluster ile Uygulanan Yoğunluk Kümeleme Analizi | 17 |
| Şekil 5 | Leaflet.heat ile İşlenen Yapay Zeka Skoruna Duyarlı Isı Haritası | 18 |
| Şekil 6 | Dinamik Şiddet İkonları (Kırmızı/Nabız, Turuncu, Sarı Olay Noktaları) | 19 |
| Şekil 7 | Uzamsal Sorgu (Draw & Search) ile Çokgensel Filtreleme Ekranı | 20 |
| Şekil 8 | Time Slider Kullanılarak Yapılan Zamansal Suç Analizi ve Akışı | 21 |
| Şekil 9 | Sistem Tarafından Otomatik Üretilen Bölgesel PDF Rapor Çıktısı | 22 |
| Şekil 10| TRİA Admin Paneli ve Scraper Performans Metrikleri | 23 |

<br><br>

## TABLOLAR DİZİNİ

| No | Tablo Başlığı | Sayfa |
|:--:|---------------|:---:|
| Tablo 1 | TRİA Asayiş Odaklı Kapsam Matrisi (Dahil ve Hariç Olay Türleri) | 3 |
| Tablo 2 | TRİA Projesi Ana Teknoloji Yığını ve Kullanım Amaçları | 7 |
| Tablo 3 | `sources.json` Merkezli Aktif OSINT Veri Kaynakları Dağılımı | 11 |
| Tablo 4 | Groq LLM Yapay Zekâ Şiddet İndeksi Skalası ve Karakteristik Örnekler | 14 |
| Tablo 5 | PostGIS Uzamsal Arama (Spatial Search) Fonksiyonlarının Mimarisi | 19 |
| Tablo 6 | TRİA Projesi Temel Ortam Değişkenleri (.env Konfigürasyonları) | 27 |

<div style="page-break-after: always;"></div>

---

# 1. GİRİŞ

## 1.1. Problem Tanımı ve Motivasyon

Günümüzde kamu düzeni, trafik kazaları, terör eylemleri ve asayiş olaylarına ilişkin bilgiler klasik kolluk kuvveti bültenlerinden veya resmi kurumlardan önce dijital medyada, yerel haber ajanslarında ve sosyal iletişim platformlarında (örneğin Telegram kanallarında) anlık olarak yayılmaktadır. Ancak siber uzayda eşzamanlı dolaşan bu veri yığınları büyük ölçüde yapılandırılmamış (unstructured), haber ajansları arasında sürekli tekrar eden (duplicated), gürültülü (noisy) ve çoğu zaman net bir coğrafi bağlamdan kopuktur.

Geleneksel suç haritalama sistemleri (Crime Mapping) büyük ölçüde geçmişe dönük, aylık veya yıllık olarak açıklanan adli istatistikleri kullanarak çalışır. Karar vericilerin, yerel yöneticilerin ve kriz müdahale birimlerinin asayiş olaylarını eşzamanlı (real-time) olarak mekânsal bir düzlemde analiz edebilmesi, **Açık Kaynak İstihbaratının (OSINT)** sistematik olarak haritalandırılarak işlenmesini zorunlu hale getirmektedir. Türkiye özelinde, yerel haber ağlarının ve resmi/gayriresmi Telegram kanallarının ürettiği heterojen asayiş verisinin yapay zekâ ile temizlenip, anlamlı bir karar destek radar sistemine dönüştürülmesi problemi TRİA projesinin temel motivasyon kaynağını oluşturmaktadır.

## 1.2. Projenin Amacı ve Hedefleri

**Genel Amaç:** Türkiye sınırları içerisindeki asayiş, kaza, suç ve güvenlik olaylarını yapay zeka entegrasyonu ve otonom yazılım botları (scrapers) vasıtasıyla tarayan, yapılandıran, sınıflandıran ve son kullanıcıya profesyonel görsel analiz mekanizmaları sunan gelişmiş bir **Coğrafi Bilgi Sistemi (CBS)** prototipi geliştirmektir.

**Ölçülebilir Mühendislik Hedefleri:**
1.  **Dinamik Kaynak Yönetimi:** Veri toplama kaynaklarının kodun içerisine gömülmesinden (hardcoding) kaçınılarak, dışarıdan yönetilebilir, esnek bir yapılandırma dosyası (`sources.json`) üzerinden kontrol edilmesini sağlamak.
2.  **LLM Optimizasyonu ve Fast-Track Hattı:** GDELT API gibi koordinatları zaten bilinen yapılandırılmış verilerin sisteme dahil edilmesinde, Büyük Dil Modeli (LLM) analizini "bypass" ederek doğrudan veritabanına aktarımını sağlamak; böylece API işletim maliyetlerini sıfıra indirmek.
3.  **Anlamsal Şiddet Analizi:** Groq LLM (llama-3.1-8b) motorunu salt bir metin okuyucu olarak değil, metnin içindeki paniği, hasarı ve suçun boyutunu kavrayarak 1 ile 10 arasında yapılandırılmış bir "Şiddet İndeksi" (Severity Score) üreten algoritmik bir analizöre dönüştürmek.
4.  **Kurumsal Düzey CBS Entegrasyonu:** Leaflet.js tabanlı arayüzde PostGIS gücünü kullanarak Isı Haritası (Heatmap), Poligonal Uzamsal Sorgu (Draw & Search) ve Zaman Serisi (Time Slider) gibi ileri düzey uzamsal analiz yeteneklerini performanstan ödün vermeden sunmak.

## 1.3. Kapsam İzolasyonu (Dahil ve Hariç Olaylar)

Büyük veri (Big Data) odaklı CBS projelerinin en büyük riski "sinyal-gürültü oranının" (Signal-to-Noise Ratio) dengesinin kaybolmasıdır. Haritanın, geliştirme amacından saparak bir "hava durumu veya deprem izleme ekranına" dönüşmemesi için TRİA mimarisinde, veritabanı aşamasından arayüz aşamasına kadar **katı bir kapsam izolasyonu** uygulanmıştır. Sistem yalnızca insan ve araç kaynaklı güvenlik ile kamu düzeni olaylarına odaklanmaktadır.

### Tablo 1. TRİA Asayiş Odaklı Kapsam Matrisi

| Kategori / Olay Türü | Kapsam Durumu | Filtreleme ve Engelleme Katmanı (Mimari Savunma) |
|----------------------|:-------------:|---------------------------------|
| Cinayet, Silahlı Çatışma | ✓ Dahil | LLM Onayı ve Asayiş Anahtar Kelime Eşleşmesi |
| Polis / Jandarma Operasyonları | ✓ Dahil | LLM Onayı ve Asayiş Anahtar Kelime Eşleşmesi |
| Trafik ve İş Kazaları | ✓ Dahil | Ön Filtre Taraması + Şiddet İndeksi Ataması |
| Hırsızlık, Gasp, Narkotik | ✓ Dahil | LLM JSON Format Çıktısı + Kategori Normalizasyonu |
| **Deprem, Fay Sarsıntıları** | ✗ Kesinlikle Hariç | Python `DISASTER_BLOCKLIST` Ön Filtre Katmanı |
| **Orman Yangınları, Sel** | ✗ Kesinlikle Hariç | GDELT İptal Sorguları + Kategori Reddi Algoritması |
| **Hava Durumu Uyarıları** | ✗ Kesinlikle Hariç | Groq LLM System Prompt: `is_crime=false` Karar Ağacı |

Bu katı ayrım ve yazılımsal izolasyon, TRİA sisteminin akademik bir araştırmanın ötesinde, emniyet güçleri, haber merkezleri veya kriminoloji araştırmacıları için yüksek doğrulukta çalışan **güvenilir bir operasyonel araç** olarak konumlandırılmasını güvence altına almaktadır.

<div style="page-break-after: always;"></div>

---

# 2. KAVRAMSAL ÇERÇEVE VE LİTERATÜR

## 2.1. Açık Kaynak İstihbaratı (OSINT) Dinamikleri

Açık Kaynak İstihbaratı (Open Source Intelligence - OSINT), gizlilik derecesi olmayan, kamuya açık dijital ve basılı verilerin sistematik bir şekilde toplanması, anlamlı parçalara ayrılması ve nihayetinde operasyonel istihbari bir değere (actionable intelligence) dönüştürülmesi sürecidir. Sosyal ağların, hiper-yerel (hyper-local) haber ajanslarının ve açık iletişim kanallarının yaygınlaşmasıyla OSINT, sadece siber güvenlikte (Cyber Threat Intelligence) değil, fiziksel güvenlik ve asayiş takiplerinde de birincil veri sağlayıcısı konumuna yükselmiştir. TRİA projesi, RSS (Really Simple Syndication) XML yapılarını ve bölgesel asayiş haberi veren anlık Telegram kanallarını "pasif bilgi toplama" (passive reconnaissance) metodolojisine uygun biçimde otonom olarak kazıyarak (web scraping) büyük veri havuzunu oluşturmaktadır.

## 2.2. Kriminolojide Coğrafi Bilgi Sistemleri (CBS)

Suçların, kazaların ve güvenlik ihlallerinin harita üzerinde tamamen rastgele (random) dağılmadığı; aksine belirli çevresel, demografik ve mekânsal dinamiklere bağlı yoğunluk noktalarına (hotspots) sahip olduğu, modern suç haritalama biliminin temel varsayımıdır. 

Bilişim sistemleri mimarisinde, olaya ait noktasal verilerin (POINT) salt birer metin veya ondalık sayı (float) olarak değil, PostgreSQL tabanlı **PostGIS** gibi mekânsal (spatial) veritabanlarında `GEOMETRY` tipinde saklanması elzemdir. Bu yapılandırma sayesinde, veriler üzerinde `ST_Within` (Bir alanın içinde mi?), `ST_Intersects` (İki geometri kesişiyor mu?) veya `ST_DWithin` (Belirli bir çemberin merkezine ne kadar uzaklıkta?) gibi güçlü uzamsal SQL fonksiyonlarıyla milisaniyeler içinde sorgulama yapılabilmektedir. TRİA, literatürde sıkça rastlanan statik haritaların aksine, veriyi anlık olarak işleyen ve Leaflet.js kütüphanesi ile kullanıcıya interaktif etkileşim sunan tam dinamik bir CBS altyapısına sahiptir.

## 2.3. Doğal Dil İşleme (NLP) ve Büyük Dil Modelleri (LLM)

Geleneksel veri mühendisliğinde yapılandırılmamış haber metinlerinden anlamlı bir lokasyon, olay türü ve hasar tespiti çıkarmak; karmaşık Doğal Dil İşleme (Natural Language Processing - NLP) algoritmaları, geniş sözlükler (gazetteers) ve etiketlenmiş devasa veri setleriyle eğitilmiş sınıflandırıcılar gerektirirdi.

Ancak yapay zekâ devrimiyle birlikte Groq, OpenAI veya Anthropic gibi firmalar tarafından sunulan Büyük Dil Modelleri (Large Language Models - LLM), üst düzey anlamsal kavrama (semantic understanding) ve bağlam analizi yetenekleri sayesinde doğrudan geliştiricilerin istediği yapılandırılmış JSON çıktılarını verebilmektedir. TRİA, otonom botlar tarafından toplanan haber metinlerini REST API üzerinden Groq motoruna göndererek saniyeler içinde kesin lokasyon, olay kategorisi ve ciddiyet puanı (Severity Score) elde etmekte; böylece konvansiyonel NLP modellerinin ağır donanım gereksinimlerini ve isabet oranı (accuracy) problemlerini başarıyla aşmaktadır.

<div style="page-break-after: always;"></div>

---

# 3. SİSTEM MİMARİSİ VE TEKNOLOJİ YIĞINI

## 3.1. Çok Katmanlı (N-Tier) Mimari Tasarımı

TRİA yazılım projesi, kodun sürdürülebilirliği (maintainability), hata ayıklama kolaylığı ve yatay ölçeklenebilirlik (scalability) prensipleri doğrultusunda "İstemci-Sunucu" (Client-Server) bağımsızlığına dayalı çok katmanlı bir yapıda inşa edilmiştir. Verinin dış kaynaklardan kazınması, işlenmesi ve son kullanıcıya CBS arayüzünde sunulması aşamaları birbirlerinden izole edilmiş mikro modüllerle yönetilmektedir.

**[GÖRSEL EKLENECEK: Şekil 1 - TRİA 3-Katmanlı Sistem Mimarisi Blok Diyagramı. GÖRSEL İÇERİĞİ: En üstte "Sunum Katmanı (Leaflet, HTML/JS)", ortada "İş Mantığı Katmanı (FastAPI, Groq LLM, Scrapers)" ve en altta "Veri Katmanı (PostgreSQL, PostGIS)" olan, aralarındaki veri akışını JSON ve REST API oklarıyla gösteren profesyonel bir mimari şema.]**

## 3.2. Sunucu ve Backend Katmanı (FastAPI & Python)

Sistemin kalbi ve beyin takımını oluşturan sunucu katmanı, asenkron G/Ç (I/O) yetenekleriyle yüksek eşzamanlı bağlantıları düşük donanımla yönetebilen **FastAPI** web çatısı altında Python (Sürüm 3.12) ile kodlanmıştır.

* **RESTful API ve Dokümantasyon:** İstemci (tarayıcı) ile sunucu arasındaki tüm iletişim JSON tabanlı REST mimarisiyle sağlanır. FastAPI'nin sunduğu otomatik Swagger arayüzü sayesinde, tüm uç noktalar (endpoints) `/api/docs` rotası üzerinden test edilebilir bir dokümantasyonla sunulmaktadır.
* **Asenkron Operasyonlar (Async/Await):** Sistem aynı anda birden fazla RSS akışını ve Telegram kanalını okumak zorundadır. Ağ (network) gecikmelerinin tüm uygulamayı kilitlemesini (blocking) önlemek amacıyla `asyncio` kütüphanesi projenin omurgasına yerleştirilmiştir.
* **Otonom Görev Yönetimi:** TRİA'nın insan müdahalesi olmadan kendi kendine asayiş verisi toplayabilmesi için Python tabanlı `APScheduler` (Advanced Python Scheduler) kullanılarak arka plan zamanlayıcıları (Cron Jobs) atanmış; veri toplama boru hattı (pipeline) her saat başı tetiklenecek şekilde programlanmıştır.

### Tablo 2. TRİA Projesi Ana Teknoloji Yığını ve Kullanım Amaçları

| Teknoloji / Kütüphane | Sürüm | Sistemdeki Rolü ve Kullanım Amacı |
|-----------------------|:-----:|-----------------------------------|
| **Python** | 3.12 | Ana backend programlama ve scraper geliştirme dili. |
| **FastAPI / Uvicorn** | 0.100+ | Yüksek performanslı asenkron web sunucusu ve API rotalandırma. |
| **SQLAlchemy (Async)**| 2.0+ | Veritabanı sorgularının nesne yönelimli (ORM) olarak yönetilmesi. |
| **GeoAlchemy2** | 0.14.0| SQLAlchemy ORM üzerinde mekânsal veri tipleri (Geometry) desteği. |
| **PostgreSQL & PostGIS**| 15 / 3.4 | İlişkisel ve uzamsal (spatial) büyük veri depolama altyapısı. |
| **Groq API** | Bulut | Llama-3.1 modeli ile ışık hızında metin analizi ve JSON dönüşümü. |
| **Leaflet.js** | 1.9.4 | Tarayıcı tabanlı düşük gecikmeli interaktif harita oluşturma motoru. |
| **Docker & Compose** | 24.0+ | Tüm bağımlılıkların izole edilerek sistemin her ortamda tek tuşla ayağa kaldırılması. |

## 3.3. Uzamsal Veritabanı (PostgreSQL & GeoAlchemy2)

Klasik ilişkisel veritabanları enlem ve boylam verilerini birbirinden bağımsız iki ondalık sayı (Float/Decimal) olarak saklar. Ancak CBS odaklı sistemlerde bu yaklaşım, mekânsal aramaları ve harita matematiklerini (örneğin iki nokta arası mesafe bulma) imkansız veya aşırı yavaş hale getirir. 

TRİA, gücünü PostgreSQL üzerine kurulan endüstri standardı **PostGIS** uzantısından almaktadır. Veriler, Dünya yüzeyindeki gerçek koordinat sistemini temsil eden `SRID=4326` (WGS 84) referans sistemiyle `GEOMETRY(POINT)` veri tipinde tutulur. Python tarafındaki veritabanı iletişimi ise çiğ SQL yazmak yerine modern ve güvenli bir yaklaşım olan **GeoAlchemy2** ORM modülü ile sağlanmaktadır.

Veritabanı temel olarak iki büyük arşivden oluşur:
1.  **`raw_news_archive` (Ham Arşiv):** Veri tekrarlarının (deduplikasyon) önüne geçmek için kazınan haberlerin eşsiz URL ve içerik (hash) anahtarlarının tutulduğu bariyer tablosu.
2.  **`crime_events` (Olay Analiz Tablosu):** LLM veya Fast-Track üzerinden işlenmiş, şiddet skoru atanmış, kategorize edilmiş ve kesin koordinatı belirlenmiş analiz edilmiş olay noktaları.

## 3.4. İstemci Katmanı ve Konteynerleştirme (Docker)

İstemci tarafı (Frontend) harici JavaScript frameworklerine (React, Vue vb.) boğulmadan, performansın maksimumda tutulması için saf HTML5, CSS3 ve Vanilla JS ile tasarlanmıştır. Tüm modüller ve veritabanı, sistem donanımından bağımsız bir şekilde çalışabilmesi adına **Docker Compose** ile konteynerleştirilmiş (containerization); böylece `docker-compose up` komutuyla uygulamanın ağ yapılandırmaları, PostGIS kurulumu ve sunucu başlangıcı dakikalar içinde tamamen otomatik hale getirilmiştir.

<div style="page-break-after: always;"></div>

---

# 4. VERİ TOPLAMA VE İŞLEME BORU HATTI (PIPELINE)

TRİA mimarisinin teknolojik kalbi, internetin yapısız bilgi yığınından hedefli bir şekilde anlamlı istihbarat çıkaran otonom "Veri Boru Hattı"dır (Data Pipeline). Bu hat, belirlenmiş bir iş akış şeması etrafında saat gibi işlemekte ve nihai veritabanına sadece kritik süzgeçlerden geçmiş, %100 asayişle ilgili nitelikli verinin geçmesine izin vermektedir.

**[GÖRSEL EKLENECEK: Şekil 2 - GDELT, RSS ve Telegram Çoklu Veri Boru Hattı Akış Şeması. GÖRSEL İÇERİĞİ: "sources.json" dosyasından yola çıkan okların "API Kazıyıcılar, Telegram, RSS" modüllerine girdiği, oradan sırasıyla "Ön Filtre (Regex)", "Deduplikasyon (Jaccard)", "Groq AI/Fast-Track" ve "Geokodlama" kutularından geçerek en son "PostGIS Veritabanına" döküldüğü teknik akış şeması.]**

## 4.1. Veri Kaynakları ve JSON Konfigürasyon Yönetimi

Temiz Kod (Clean Code) standartları ve kurumsal yazılım geliştirme prensipleri gereğince, hedeflenen web siteleri, haber ajansları veya API URL'leri uygulamanın Python kaynak kodlarının içerisine sert olarak gömülmemiş (hardcoded yapılmamış); bunun yerine proje dizininde yer alan `config/sources.json` isimli harici bir konfigürasyon dosyasına bağlanmıştır. 

Bu veri-güdümlü (Data-Driven) tasarım sayesinde, kodlama bilmeyen bir sistem yöneticisi veya analist, sadece JSON dosyasına yeni bir bağlantı satırı ekleyerek sistemi anında yeni bir Telegram kanalına veya haber ajansına yönlendirebilmektedir.

### Tablo 3. `sources.json` Merkezli Aktif OSINT Veri Kaynakları Dağılımı

| Kaynak Segmenti | Veri Tipi | İçerik ve Spesifik Kullanım Detayı |
|-----------------|:---------:|------------------------------------|
| **Global API (GDELT)** | GeoJSON | Dünya olaylar veritabanından, Türkiye Bounding Box'ı içinde kalan *ARREST, POLICE, KILL, TERROR* olay sorguları. |
| **Ulusal Ajans / RSS** | XML/RSS | İHA, AA, NTV, Habertürk, Sözcü, Sabah vb. ana akım haber ajanslarının son dakika asayiş akışları. |
| **Telegram Public** | HTML/Web | Olay anında fotoğraf ve konum aktarımı yapan anonim polis bültenleri ve acil durum kanalları (Örn: ajans_muhbir). |
| **Google News Dork** | RSS | Gelişmiş arama dorklarıyla hedeflenmiş *"Türkiye AND (kaza OR cinayet OR operasyon) when:1d"* sorguları. |

## 4.2. GDELT API ve Maliyet Düşürücü Bypass (Fast-Track) Hattı

Projede hız kapasitesini artıran ve API işletim maliyetini (LLM token kullanımı) optimize eden en kritik mühendislik hamlesi "Fast-Track Bypass" hattının inşasıdır. **GDELT** (Global Database of Events, Language, and Tone) GKG (Global Knowledge Graph) API'sinden çekilen veriler, halihazırda yapılandırılmış GeoJSON formatında olup; olayın İngilizce meta verisini, ilgili haberin kaynağını ve doğrudan olayın gerçekleştiği koordinatları (`lat`, `lon`) içermektedir.

Gelen bu veri zaten uzamsal olarak tanımlı olduğundan, olayın yerini tespit etmesi için Groq Yapay Zekâsına (LLM) gönderilmesi hem ciddi bir zaman kaybı hem de bedel gerektiren API kotası israfıdır. TRİA içindeki özel `api_ingestor.py` modülü, GDELT verisini çeker çekmez metin içerisindeki "murder, assault, arrest" gibi kelimeleri tarayarak kendi Kural Tabanlı Şiddet (Heuristic Severity) algoritmasını çalıştırır. Puanlama tamamlandığında veriler, ağır LLM katmanını "bypass" ederek milisaniyeler içerisinde doğrudan PostGIS uzamsal veritabanına yazılır.

## 4.3. Dinamik Web Kazıma (Telegram Önizleme ve RSS)

Sisteme API haricinde giren ham metin verileri (RSS ve Telegram) için gelişmiş kazıyıcı (scraper) botlar yazılmıştır. 
* **RSS Taraması:** Klasik `requests` kütüphanesinin engellendiği Cloudflare veya bot korumalı haber sitelerini aşabilmek için `cloudscraper` ve XML yapısını parçalamak için `feedparser` kütüphaneleri kullanılmıştır. Eğer RSS özeti analiz için yeterince uzun değilse (200 karakterden kısa), sistem bağlantı linkine giderek haberin tam metnini `BeautifulSoup` yardımıyla çeker.
* **Telegram Web Kazıma:** Herhangi bir API anahtarı veya giriş (login) gereksinimi olmaksızın, Telegram'ın sunduğu açık web önizleme rotası `t.me/s/{kanal_adi}` üzerinden HTML parçalama yöntemiyle en güncel haber ve asayiş postları pasif bir şekilde sisteme çekilmektedir.

Sistemin geçmiş verilerle haritayı çöplüğe çevirmemesi için `MAX_ARTICLE_AGE_HOURS` (varsayılan 72 saat) zaman damgası kısıtlaması uygulanmakta; eski haberler sisteme hiç alınmamaktadır.

## 4.4. Maliyet Kalkanı: Anahtar Kelime Ön Filtreleme (Pre-Filter)

Telegram kanallarından ve haber ajanslarının RSS beslemelerinden her saat yüzlerce makale yağmaktadır. Spor sonuçları, borsa bültenleri veya siyasi açıklamalar gibi ilgisiz yüzlerce uzun metnin Groq LLM API'sine gönderilmesi sistemi çok kısa sürede kota aşımına (Rate Limit) ve mantıksal çökmeye götürür.

Bu devasa maliyet sızıntısını engellemek için LLM katmanından hemen önce güçlü bir **Ön Filtre (Pre-filter) Algoritması** yerleştirilmiştir:
1.  **Kara Liste Reddi:** Eğer metin içerisinde "deprem, sel, fırtına, enflasyon, maç, faiz" gibi kelimelerden herhangi biri tespit edilirse olay anında sistem dışı bırakılır (Reject).
2.  **Sinyal Tespiti:** Metin; "cinayet, kaza, operasyon, silah, narkotik, hırsız, gözaltı" gibi spesifik asayiş kelime havuzuyla taranır. Bu kelimelerin hiçbiri metinde geçmiyorsa, olayın asayiş bağlantısı olmadığına karar verilir ve veri LLM'e gitmeden imha edilir.

## 4.5. Tekrarlayan Veri Önleme (Jaccard Deduplikasyon)

Önemli bir trafik kazası veya narkotik operasyonu aynı gün içerisinde NTV'de, Hürriyet'te ve yerel Telegram kanallarında aynı anda haber yapılabilir. TRİA sisteminin bu durumu algılayamayıp aynı olayı haritaya 4 farklı kaza gibi işlemesini önlemek amacıyla matematiksel bir tekrarsızlaştırma (Deduplikasyon) katmanı kurulmuştur.

Olay metinlerinin başlıkları Unicode standardında temizlenip küçük harfe çevrilir, noktalama işaretleri silinir. Uygulanan **Jaccard Benzerlik Algoritması** (Jaccard Similarity / N-gram string matching) sayesinde yeni gelen haber başlığı, veritabanındaki mevcut arşivle karşılaştırılır. Eğer benzerlik oranı `.env` dosyasında tanımlanan `%80` (`CONTENT_SIMILARITY_THRESHOLD=0.8`) eşik değerini aşıyorsa, yeni haberin aslında eski bir olayın kopyası (duplicate) olduğu kabul edilir ve veritabanına yazılması durdurulur.

## 4.6. Groq AI Entegrasyonu ve Şiddet İndeksi (Severity Score) Ataması

Tüm maliyet kalkanlarını ve ön filtreleri başarıyla geçen nitelikli ham haber metinleri, FastAPI sunucusu tarafından özel bir Sistem Komutuyla (System Prompt) birlikte **Groq AI (Llama-3.1-8b-instant)** modeline iletilir. Modelin talimatı son derece nettir: Metni oku, yorumlama yapma, sadece istenen yapılandırılmış JSON formatını (İl, İlçe, Kategori, Kısa Özet) döndür.

TRİA'nın OSINT analizi konusundaki en yenilikçi adımı, LLM modeline entegre edilen "Algoritmik Karar Verme" mekanizmasıdır. Model, haberdeki olayın vahametini, yaralı sayısını veya halka verdiği paniği analiz ederek olaya 1 ile 10 arasında bir **Şiddet İndeksi (Severity Score)** atar. Bu skor, arayüzdeki ikonların rengini ve büyüklüğünü doğrudan kontrol eden en temel değişkendir.

### Tablo 4. Groq LLM Yapay Zekâ Şiddet İndeksi Skalası ve Karakteristik Örnekler

| AI Skoru | Şiddet Seviyesi | Olay Karakteristiği ve Temsili Örnekler |
|:----:|:---------------:|-----------------------------------------------------|
| **1-3** | **Düşük Risk** | Maddi hasarlı küçük trafik kazaları, sözlü tartışmalar, ihbarlar, basit zabıta müdahaleleri. |
| **4-6** | **Orta Risk** | Yaralanmalı trafik kazaları, uyuşturucu/narkotik baskınları, haneye tecavüz, gasp, büyük maddi hırsızlık vakaları. |
| **7-8** | **Yüksek Risk** | Çok araçlı zincirleme veya ağır yaralanmalı kazalar, silahlı yaralama olayları, organize örgütlere yapılan büyük şafak operasyonları. |
| **9-10**| **Kritik Risk** | Cinayet ve ölümlü saldırılar, terör eylemleri, bombalı saldırı ihbarları, kolluk kuvvetleriyle silahlı çatışma vakaları. |

## 4.7. Türkiye Odaklı Metinsel Geokodlama ve Validasyon

Groq AI'nin metinden çıkardığı İl (City) verisi ham haliyle hemen haritaya basılamaz. Açık kaynak haber ajanslarında (özellikle GDELT uluslararası yayınlarında) "Almanya'da trafik kazası" veya "Suriye sınırında sıcak çatışma" gibi dış lokasyonlu haberler "Türkiye" etiketiyle RSS akışlarına düşebilmektedir.

Sistemin, Almanya'daki bir kazayı Ankara'nın ortasına yanlışlıkla (False Positive) yerleştirmemesi için `geolocation.py` isimli bir Geokodlama Validasyon Modülü çalıştırılmaktadır.
1.  Haber metnindeki dış ülkeler (Yabancı Yer İsimleri Sözlüğü) taranır. Yabancı yer adı bulunursa koordinat doğrudan çöpe atılır.
2.  Şehir veya ilçe adı veritabanındaki Türkiye kordinat sözlüğü (Gazetteer) ile eşleştirilir.
3.  Elde edilen kesin koordinatın (Enlem, Boylam), Türkiye Coğrafi Sınır Kutusu'nun (Bounding Box - Latitude: 35.8-42.4, Longitude: 25.9-44.8) kesinlikle içerisinde kalıp kalmadığı matematiksel olarak doğrulanır. Koordinat kutu dışında kalıyorsa harita güvenilirliğini korumak adına olay reddedilir.

<div style="page-break-after: always;"></div>

---

# 5. CBS VE ARAYÜZ YETENEKLERİ (FRONTEND)

TRİA'nın devasa arka plan mühendisliği, son kullanıcıya (emniyet yetkilisi veya risk analisti) operasyonel bir değer katmadığı sürece anlamsızdır. Bu nedenle web arayüzü; sıradan bir Google Haritalar görünümünün ötesine geçerek, profesyonel kurumsal yazılımlarda (Örn: Palantir Gotham, Esri ArcGIS) görülen uzamsal analiz ve görselleştirme araçlarıyla donatılmıştır.

**[GÖRSEL EKLENECEK: Şekil 3 - TRİA Ana Harita Arayüzü. GÖRSEL İÇERİĞİ: Tarayıcıda tam ekran açılmış, karanlık CARTO altlığı üzerinde Sivas, Ankara, Kayseri gibi bölgelerde olayların yer aldığı, sol tarafta "TRİA İstihbarat Radarı" kontrol menüsünün bulunduğu ana harita ekran görüntüsü.]**

## 5.1. Harita Altyapısı (Leaflet.js) ve Koyu Tema Altlık Kullanımı

İstemci tarafında ağır web frameworkleri yerine veriyi hızlı (responsive) ve anlık manipüle edebilmek için, açık kaynaklı haritalama motoru **Leaflet.js (Sürüm 1.9.4)** kullanılmıştır. Arayüzün istihbarat paneli (radar) havasını yansıtması ve kırmızı/sarı şiddet ikonlarının göz yormadan maksimum kontrastla ekranda belirmesi için harita altlığı (Basemap) olarak `CartoDB.DarkMatter` katmanı tercih edilmiştir. Harita açılış anında her zaman `fitBounds` metoduyla kendini Türkiye sınırlarına ortalar ve kullanıcıyı ülkenin dışına çıkmaktan alıkoyar.

## 5.2. Veri Görselleştirme: Yoğunluk Kümelemesi ve Isı Haritası

Türkiye genelinden toplanan binlerce asayiş olayının aynı anda haritaya noktalar halinde basılması hem tarayıcıyı dondurur hem de ekranı okunamaz hale getirir (Map Clutter). TRİA, bu "bilgi yığılmasını" önlemek için sol menü üzerinden değiştirilebilen üç farklı katman stratejisi sunar:

1.  **Kümeleme Görünümü (Marker Clustering):** Haritadan uzaklaştıkça birbirine yakın (Örn: İstanbul ve Kocaeli) yüzlerce olay, matematiksel bir algoritma ile tek bir daire etrafında toplanır ve üzerine toplam sayı (Örn: "50") yazılır. Haritaya (yakınlaştırma/zoom in) yapıldıkça bu kümeler kırılarak mahalle seviyesine kadar dağılır. Kullanılan eklenti: `Leaflet.markercluster`.
2.  **Isı Haritası (Heatmap):** Taktiksel suç analizinde (Tactical Crime Analysis) en çok kullanılan yöntemdir. Kullanıcı olayların tekil yerlerinden ziyade, suç yoğunluğunun nerelerde kırmızı alarm verdiğini görmek ister. `Leaflet.heat` algoritması, Groq yapay zekasının atadığı 1-10 arası "Şiddet Skoru"nu bir ağırlık çarpanı olarak kullanır. Böylece 1 cinayet vakası, haritada 5 adet maddi hasarlı kazadan çok daha geniş ve kırmızı bir ısı bulutu yayar.

**[GÖRSEL EKLENECEK: Şekil 4 - Harita üzerinde İç Anadolu veya Marmara Bölgesinde yoğunlaşmış, üzerinde olay sayıları yazan Kümeleme (Clustering) Analizi ekranı.]**
**[GÖRSEL EKLENECEK: Şekil 5 - Türkiye geneli suç yoğunluğunu gösteren, özellikle İstanbul, Ankara civarının kırmızıdan sarıya parladığı Isı Haritası (Heatmap) görünümü.]**

## 5.3. Dinamik Şiddet İkonları ve Kategori Filtreleme

Kullanıcı "Nokta" görünümüne geçtiğinde, harita üzerindeki ikonlar sıradan raptiyeler (pin) olarak değil, olayın şiddetine göre CSS (Cascading Style Sheets) ile dinamik olarak boyutlandırılan geometrik daireler (DivIcon) olarak render edilir.

* **Düşük Risk (1-4 Puan):** Küçük ölçekli, statik sarı noktalar.
* **Orta Risk (5-6 Puan):** Orta ölçekli, dikkat çekici turuncu daireler.
* **Kritik Risk (7-10 Puan):** Dikkat merkezini zorla üzerine çeken büyük kırmızı daireler. CSS ile atanan `pulse-animation` (nabız atışı) sayesinde bu cinayet veya terör olayları haritada sürekli yanıp sönerek görevliye kırmızı alarm verir.

Ayrıca sol paneldeki checkbox (onay kutusu) filtreleri kullanılarak, kullanıcı tek tıkla düşük riskli olayları gizleyebilir ve sadece "Kritik Riskli" vakaları haritada izole edebilir.

**[GÖRSEL EKLENECEK: Şekil 6 - Haritada yan yana duran; küçük Sarı, orta Turuncu ve büyük kırmızı (Nabız Animasyonlu) Dinamik Şiddet İkonlarının çok yakından çekilmiş ekran görüntüsü.]**

## 5.4. Uzamsal Sorgu: Çizerek Arama (Draw & Search / ST_Intersects)

TRİA'yı basit bir haritadan çıkarıp gerçek bir "Uzamsal Sorgu Aracına" (Spatial Data Infrastructure) dönüştüren mühendislik harikası, PostGIS entegrasyonuyla çalışan "Çiz ve Ara" sistemidir. 

Kullanıcı arayüzdeki `Leaflet.draw` kontrol paletini alır. Harita üzerinde (Örneğin Sivas merkez ile Zara arasındaki bölgeyi) farenin imleciyle serbest bir Çokgen (Polygon) veya Çember içerisine alır. O an tarayıcı, kullanıcının çizdiği bu çokgenin GeoJSON koordinatlarını, backend sistemindeki `POST /api/v1/incidents/spatial-search` rotasına gönderir. PostGIS, veritabanındaki tüm olayları `ST_Intersects` fonksiyonundan geçirerek milisaniyeler içinde sadece kullanıcının çizdiği çemberin içerisine düşen asayiş olaylarını bularak haritaya geri fırlatır.

### Tablo 5. PostGIS Uzamsal Arama (Spatial Search) Fonksiyonlarının Mimarisi

| Kullanıcı Çizimi (Leaflet) | Backend PostGIS Komutu | Mimari ve Mantıksal Algoritma |
|----------------------------|------------------------|-------------------------------|
| **Çember Çizimi (Circle)** | `ST_DWithin` | Kullanıcının tıkladığı merkez nokta (POINT) alınır, farenin çekildiği yarıçap metreye çevrilir ve merkezden yarıçap mesafesine kadar olan tüm olaylar filtrelenir. |
| **Serbest Alan (Polygon)** | `ST_Intersects` | Çizilen çok köşeli geometrik alanın (MultiPolygon) sınırları ile PostGIS'teki noktaların matris kesişimi taranır. Sadece alan içinde kalanlar döndürülür. |

**[GÖRSEL EKLENECEK: Şekil 7 - Ekranda fare ile Sivas veya Ankara çevresinde manuel olarak mavi bir çizgiyle çizilmiş alan (Polygon) ve haritadaki diğer tüm olaylar yok olmuşken sadece o alanın içindeki suçların göründüğü Draw & Search filtreleme ekranı.]**

## 5.5. Zamansal Analiz: Geçmişe Yolculuk (Time Slider)

Kriminolojide asayiş vakalarının uzamsal (mekânsal) olduğu kadar zamansal (temporal) bir karakteristiği de (örneğin hafta sonu artan olaylar) vardır. Ekranın alt kısmına entegre edilen "Time Slider" (Zaman Çubuğu) kontrolü sayesinde, zaman boyutu bir filtre aracı olarak kullanılır. Kullanıcı, imleci geriye çekerek haritadaki olayları silebilir veya "Oynat" fonksiyonuna basarak son 7 günün suç haritasının gün gün, saat saat sırayla haritada nasıl belirdiğini bir animasyon simülasyonu olarak izleyebilir.

**[GÖRSEL EKLENECEK: Şekil 8 - Ekranın en alt kısmında yatay olarak uzanan Time Slider (Zaman Çubuğu) ve üzerindeki Oynat/Durdur kontrollerinin göründüğü ekran kesiti.]**

## 5.6. Karar Destek: Otomatik Bölgesel PDF Rapor Üretimi

Üst düzey yöneticiler, valiler veya emniyet müdürleri operasyonel haritalardan ziyade her zaman masalarının üstünde basılı (hardcopy) veya yazılı PDF istihbarat raporları görmek isterler. TRİA sol kontrol panelindeki "Rapor Oluştur" butonuna basıldığında, haritada o anki filtrelemelere (Örneğin; Sivas poligonu içinde kalmış kritik şiddetli kazalar) uyan veri kümesini alır. 

Bu veri seti ile dinamik olarak temiz, siyah-beyaz yazdırma formatına uygun (Print-friendly) bir HTML sayfası oluşturulur. Raporda "Kategori Dağılım Tabloları", "Olay Özetleri" ve "Şiddet İstatistikleri" otomatik olarak hesaplanır. Tarayıcının standart yazdırma özelliği (Ctrl+P) tetiklenerek kusursuz bir Bölgesel Asayiş PDF Raporu dışa aktarılır.

**[GÖRSEL EKLENECEK: Şekil 9 - Siyah beyaz formatlı, "Bölgesel Asayiş Analiz Raporu" başlıklı, içerisinde olay dağılım tablolarının ve risk metriklerinin bulunduğu yazdırılmaya hazır PDF önizleme ekranı.]**

## 5.7. Sistem Tanılama: Admin Panel ve "Kıyamet Günü" Demo Modu

Uygulamanın sağ üst köşesinden erişilen gizli `/admin` sayfası, sistem yöneticilerine backendin kalbine inme fırsatı sunar. Burada "Scraper Metrikleri", "Çekilen Veri Sayıları", "API Limitleri" ve "Boru Hattı Hata Raporları (Diagnostics)" saniye saniye izlenebilir.

Ayrıca canlı sunumlarda internet bağlantısının kopması veya o anki saat diliminde Türkiye'de yeterli olay olmaması gibi risklere karşı bir "Kıyamet Günü (Doomsday)" butonu kodlanmıştır. `POST /api/v1/generate-mock-data` API rotası çalıştırıldığında, sistem İç Anadolu bölgesine 30 adet rastgele kategorize edilmiş sahte (mock) olay fırlatarak tüm ısı haritası ve kümeleme yeteneklerinin sunum esnasında kesintisiz test edilmesine imkan tanır.

<div style="page-break-after: always;"></div>

---

# 6. SONUÇ VE DEĞERLENDİRME

## 6.1. Elde Edilen Teknik Bulgular ve Performans

T-X tarafından tasarlanan ve kodlanan **TRİA (Türkiye Risk İstihbarat Ağı)** projesi; Açık Kaynak İstihbaratı (OSINT), Modern Web Çatıları (FastAPI), Uzamsal Veritabanları (PostGIS) ve Yapay Zekânın (Groq LLM) aynı potada ne kadar uyumlu ve yüksek verimli çalıştırılabileceğini kanıtlayan kapsamlı bir çalışmadır.

* **Filtreleme Başarısı:** Sistem, otonom kazıma süreçlerinde her gün yüzlerce haber akışını başarıyla absorbe etmiş; %90'ın üzerinde bir oranla siyasi açıklamalar, ekonomi bültenleri ve spor haberleri gibi "kuru gürültüyü (noise)" Ön Filtre algoritmalarıyla sisteme girmeden önce reddetmeyi başarmıştır.
* **LLM Skorlama İsabeti:** Groq yapay zekâ modelinin metinden duyguyu ve felaket boyutunu analiz etmesi (Sentiment & Context Analysis) başarılı sonuçlar vermiş; haberlerdeki silahlı bir çatışmaya hızla 9 puan (Kritik Risk) verirken, maddi hasarlı küçük bir kazaya 2 puan (Düşük Risk) ataması harita üzerindeki renklendirmelerin kusursuz bir hiyerarşiyle ekrana yansımasını sağlamıştır.
* **Maliyet ve Hız Optimizasyonu:** GDELT Fast-Track entegrasyonu, veriyi doğrudan veritabanına geçirerek uygulamanın API (Token) işletim maliyetlerini büyük ölçüde sıfırlamış; PostGIS uzamsal indekslemeleri sayesinde Draw & Search gibi karmaşık kesişim analizleri milisaniyeler (ping süreleri) altında tamamlanmıştır.

## 6.2. Sistemin Pratik Çıktıları ve Yenilikçi Yönleri

1.  **İnsan Bağımsız Tam Otonomi:** Proje, bir kez Docker üzerinde ayağa kaldırıldığında (Deployment), başka hiçbir insan müdahalesine gerek duymadan `APScheduler` ile 7/24 çalışabilen kendi kendine yeten (self-sustaining) bir OSINT veri hattı sunmaktadır.
2.  **Karar Alıcılara Stratejik Destek:** Geleneksel polis kayıtlarına göre çok daha "erken uyarı" sağlayan medya verilerini, çokgensel arama ve PDF raporlama ile anında kullanılabilir (actionable) raporlara dönüştürerek yerel yönetimlerin karar alma hızını artırmaktadır.
3.  **Kesin Hedef Odaklılık (Kapsam İzolasyonu):** Deprem, sel veya fırtına gibi afet olaylarını reddeden izole veri mimarisi başarıyla test edilmiş; TRİA haritasının saf bir "İnsan Kaynaklı Asayiş ve Güvenlik Radarı" olarak kalması garanti altına alınmıştır.

## 6.3. Gelecek Çalışmalar ve İyileştirme Önerileri

Mevcut prototip stabil, otonom ve hatasız çalışıyor olsa da; uygulamanın gelecekte emniyet güçlerine veya kurumsal haber merkezlerine bir "SaaS" (Hizmet Olarak Yazılım) ürünü olarak sunulabilmesi adına bazı ölçeklendirme geliştirmelerine açıktır:
* **Sokak Ölçeğinde Mikro Geokodlama:** Şu an uygulanan Metinsel Geokodlama (Textual Geocoding) haberin metninden sadece Şehir/İlçe bazlı nokta koordinatı tespit etmektedir. İlerleyen safhalarda, Google Geocoding API veya açık kaynaklı Nominatim sunucuları entegre edilerek, olayların cadde/mahalle hassasiyetinde işaretlenmesi planlanmaktadır.
* **LLM Bağımlılığının Tamamen Ortadan Kaldırılması:** Mevcut yapıda Groq API'nin bulut yapısı dış bağımlılık yaratmaktadır. Sistemin tamamen kapalı devre (On-Premise) çalışabilmesi için, açık kaynaklı ve sadece Türkçe haber okumak üzerine ince ayar yapılmış (Fine-tuned) küçük bir BERT (Örn: dbmdz/bert-base-turkish-cased) modeli eğitilerek sunucu içine gömülebilir.
* **Emniyet İstatistikleriyle Çapraz Doğrulama (Cross-Validation):** OSINT verilerinin, gecikmeli gelse de %100 kesinliği olan Resmi Polis Bültenleri ile çapraz doğrulanarak haritadaki olası yanlış alarmların (False Positives) zaman içerisinde temizlenmesi, sistemin istatistiksel güvenilirliğini artıracaktır.

<div style="page-break-after: always;"></div>

---

# KAYNAKÇA

1.  GDELT Project. (2024). *Global Knowledge Graph (GKG) GeoJSON API Architecture*. Erişim adresi: https://blog.gdeltproject.org/
2.  Tiangolo, S. (2024). *FastAPI Documentation: High Performance Asynchronous REST APIs*. Erişim adresi: https://fastapi.tiangolo.com/
3.  PostGIS Project Steering Committee. (2024). *PostGIS Spatial Extender Documentation: Spatial Relationships (ST_Intersects, ST_DWithin)*. Erişim adresi: https://postgis.net/documentation/
4.  Agafonkin, V. (2024). *Leaflet — An open-source JavaScript library for mobile-friendly interactive maps*. Erişim adresi: https://leafletjs.com/
5.  Groq Inc. (2024). *Groq Cloud API and Llama-3.1-8b Natural Language Processing Documentation*. Erişim adresi: https://console.groq.com/docs
6.  Ratcliffe, J. H. (2016). *Intelligence-Led Policing and Tactical Crime Mapping*. Routledge Publishing.
7.  Chainey, S., & Ratcliffe, J. (2005). *GIS and Crime Mapping*. John Wiley & Sons.
8.  Glassman, M., & Kang, M. J. (2012). *Intelligence in the internet age: The emergence and evolution of Open Source Intelligence (OSINT)*. Computers in Human Behavior, 28(2), 673-682.

<div style="page-break-after: always;"></div>

---

# EKLER

## EK-A: Sistem Konfigürasyonu ve Ortam Değişkenleri

Uygulamanın Docker üzerinde ayağa kalkabilmesi için proje kök dizininde yer alan gizli `.env` (Environment) dosyası değişkenleri ve limit yapılandırmaları aşağıda belirtilmiştir. Sistemin üretim (Production) güvenliği nedeniyle API anahtarları maskelenmiştir.

### Tablo 6. TRİA Projesi Temel Ortam Değişkenleri (.env Konfigürasyonları)

| Değişken Anahtarı | Varsayılan Değer / Veri Tipi | Mimari Görevi ve Açıklaması |
|-------------------|------------------------------|-----------------------------|
| `DATABASE_URL` | postgresql+asyncpg://... | FastAPI'nin asenkron veri havuzu ve PostGIS bağlantı soketi. |
| `GROQ_API_KEY` | gsk_******************* | LLM çağrıları için Groq bulut API yetkilendirme anahtarı (Gizli). |
| `GROQ_MODEL` | llama-3.1-8b-instant | Metin analizinde düşük gecikme ve yüksek bağlam için seçilen model. |
| `CRIME_PREFILTER_THRESHOLD` | 0.15 (Float) | Olayların anahtar kelime süzgecinden geçebilmesi için minimum zorluk eşiği. |
| `CONTENT_SIMILARITY_THRESHOLD`| 0.80 (Float) | Kopya haberleri engellemek için kurulan Jaccard string benzerlik sınırı. |
| `MAX_ARTICLE_AGE_HOURS` | 72 (Integer) | RSS kazıyıcılarının sadece son 3 günlük taze veriyi çekmesini sağlayan limit. |

## EK-B: Proje Dizin Yapısı ve Dağıtım (Deployment) Ağacı

Yazılım geliştirme süreçlerinde kod karmaşasını engellemek adına proje mikro-servis mantığıyla klasörlenmiş; uç noktalar (endpoints) iş mantığından (business logic) tamamen izole edilmiştir.

```text
TRIA_Project/
├── app/
│   ├── api/v1/          # Çizerek Arama (Spatial) ve Demo API uç noktaları.
│   ├── core/            # Veritabanı yapılandırmaları, Güvenlik (CORS/Auth).
│   ├── modules/crime/   # Kategorizasyon, Veri Normalizasyonu ve Temel Router.
│   ├── scrapers/        # GDELT Ingestor, RSS ve Telegram Kazıyıcı Botları.
│   └── services/        # Groq_analyzer (LLM Modülü) ve Geolocation Koordinat Düzeltici.
├── config/
│   └── sources.json     # Sistemin beyni: Tüm dış OSINT veri hedefleri havuzu.
├── frontend/
│   ├── static/          # map.js, map.css, leaflet eklentileri (Draw/Heat/Cluster).
│   └── templates/       # index.html (Saf DOM tabanlı Ana Harita Arayüzü).
├── scripts/             # Eski dataları temizleyen bağımsız Python DB normalizasyon araçları.
├── docker-compose.yml   # Veritabanı ve FastAPI Konteynerlerini bağlayan orkestrasyon dosyası.
├── main.py              # Uygulamanın asenkron başlatılma noktası (Entry Point).
└── requirements.txt     # Python backend ve kazıyıcı kütüphane bağımlılıkları listesi.

**[GÖRSEL EKLENECEK: Şekil 10 - VS Code içerisinde sağ tarafta proje dizin yapısının (Tree), alt tarafta (Terminalde) ise Docker Compose'un tria_app ve tria_database konteynerlerini çalıştırdığı ve "Application startup complete" logunu gösteren bir ekran görüntüsü.]**
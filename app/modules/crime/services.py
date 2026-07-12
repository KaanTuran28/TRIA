import os
import re
from typing import Any

CITY_COORDS: dict[str, tuple[float, float]] = {
    "adana": (37.0, 35.3213),
    "adiyaman": (37.7648, 38.2786),
    "afyonkarahisar": (38.7507, 30.5567),
    "agri": (39.7191, 43.0503),
    "aksaray": (38.3687, 34.0360),
    "amasya": (40.6499, 35.8353),
    "ankara": (39.9334, 32.8597),
    "antalya": (36.8969, 30.7133),
    "ardahan": (41.1105, 42.7022),
    "artvin": (41.1828, 41.8183),
    "aydin": (37.8560, 27.8416),
    "balikesir": (39.6484, 27.8826),
    "bartin": (41.6344, 32.3375),
    "batman": (37.8812, 41.1351),
    "bayburt": (40.2552, 40.2249),
    "bilecik": (40.0567, 30.0665),
    "bingol": (38.8853, 40.4983),
    "bitlis": (38.4006, 42.1095),
    "bolu": (40.7395, 31.6116),
    "burdur": (37.7203, 30.2908),
    "bursa": (40.1885, 29.0610),
    "canakkale": (40.1553, 26.4142),
    "cankiri": (40.6013, 33.6134),
    "corum": (40.5506, 34.9556),
    "denizli": (37.7765, 29.0864),
    "diyarbakir": (37.9144, 40.2306),
    "duzce": (40.8438, 31.1565),
    "edirne": (41.6771, 26.5557),
    "elazig": (38.6810, 39.2264),
    "erzincan": (39.7500, 39.5000),
    "erzurum": (39.9055, 41.2658),
    "eskisehir": (39.7767, 30.5206),
    "gaziantep": (37.0662, 37.3833),
    "giresun": (40.9128, 38.3895),
    "gumushane": (40.4386, 39.5086),
    "hakkari": (37.5744, 43.7408),
    "hatay": (36.4018, 36.3498),
    "igdir": (39.8880, 44.0048),
    "isparta": (37.7648, 30.5566),
    "istanbul": (41.0082, 28.9784),
    "izmir": (38.4237, 27.1428),
    "kahramanmaras": (37.5858, 36.9371),
    "karabuk": (41.2061, 32.6204),
    "karaman": (37.1759, 33.2287),
    "kars": (40.6013, 43.0975),
    "kastamonu": (41.3887, 33.7827),
    "kayseri": (38.7312, 35.4787),
    "kilis": (36.7165, 37.1147),
    "kirikkale": (39.8468, 33.5153),
    "kirklareli": (41.7333, 27.2167),
    "kirsehir": (39.1425, 34.1709),
    "kocaeli": (40.8533, 29.8815),
    "konya": (37.8746, 32.4932),
    "kutahya": (39.4167, 29.9833),
    "malatya": (38.3552, 38.3095),
    "manisa": (38.6191, 27.4289),
    "mardin": (37.3212, 40.7245),
    "mersin": (36.8121, 34.6415),
    "mugla": (37.2153, 28.3636),
    "mus": (38.9462, 41.7539),
    "nevsehir": (38.6939, 34.6857),
    "nigde": (37.9667, 34.6833),
    "ordu": (40.9839, 37.8764),
    "osmaniye": (37.0742, 36.2478),
    "rize": (41.0201, 40.5234),
    "sakarya": (40.7569, 30.3781),
    "samsun": (41.2867, 36.3300),
    "sanliurfa": (37.1591, 38.7969),
    "siirt": (37.9333, 41.9500),
    "sinop": (42.0231, 35.1531),
    "sivas": (39.7477, 37.0179),
    "sirnak": (37.5164, 42.4611),
    "tekirdag": (40.9833, 27.5167),
    "tokat": (40.3167, 36.5500),
    "trabzon": (41.0027, 39.7168),
    "tunceli": (39.1079, 39.5401),
    "usak": (38.6823, 29.4082),
    "van": (38.4891, 43.4089),
    "yalova": (40.6500, 29.2667),
    "yozgat": (39.8181, 34.8147),
    "zonguldak": (41.4564, 31.7987),
}

# Yalnizca asayis / suc / polis operasyonu (afet, deprem, hava disi)
CRIME_KEYWORDS = (
    "kaza",
    "cinayet",
    "operasyon",
    "silah",
    "polis",
    "jandarma",
    "kavga",
    "uyusturucu",
    "uyuşturucu",
    "hirsizlik",
    "hırsızlık",
    "dolandiricilik",
    "dolandırıcılık",
    "dolandir",
    "dolandır",
    "gaspa",
    "soygun",
    "gozalti",
    "gözaltı",
    "asayis",
    "asayiş",
    "yangin",
    "yangın",
    "patlama",
    "mahkeme",
    "tutukla",
    "supheli",
    "şüpheli",
)

DISASTER_BLOCKLIST = (
    "deprem",
    "afet",
    "sel",
    "heyelan",
    "kandilli",
    "afad",
    "tsunami",
    "hava durumu",
    "meteoroloji",
)
# Not: yangin/patlama artik bloklanmiyor — C4I'da "fire_anomaly" olarak izlenir.


def _normalize_city(name: str | None) -> str | None:
    if not name:
        return None
    key = (
        name.strip()
        .lower()
        .replace("ı", "i")
        .replace("ğ", "g")
        .replace("ü", "u")
        .replace("ş", "s")
        .replace("ö", "o")
        .replace("ç", "c")
    )
    return key if key in CITY_COORDS else key


def _keyword_in_text(kw: str, text: str) -> bool:
    """Kisa kelimelerde (sel, olum) yanlis pozitifleri onlemek icin kelime siniri."""
    if len(kw) <= 4:
        return bool(re.search(rf"\b{re.escape(kw)}\b", text))
    return kw in text


def crime_prefilter_score(title: str, summary: str) -> float:
    text = f"{title} {summary}".lower()
    hits = sum(1 for kw in CRIME_KEYWORDS if _keyword_in_text(kw, text))
    return min(1.0, hits / 3.0)


def passes_crime_prefilter(title: str, summary: str) -> bool:
    """
  LLM maliyet kalkani: en az bir asayis anahtar kelimesi; afet/deprem metinleri reddedilir.
    """
    text = f"{title} {summary}".lower()
    if any(_keyword_in_text(kw, text) for kw in DISASTER_BLOCKLIST):
        return False
    if not any(_keyword_in_text(kw, text) for kw in CRIME_KEYWORDS):
        return False
    threshold = float(os.getenv("CRIME_PREFILTER_THRESHOLD", "0.15"))
    if threshold <= 0:
        return True
    return crime_prefilter_score(title, summary) >= threshold


def parse_raw_news(title: str, content: str, source: str) -> dict[str, Any] | None:
    from app.services.groq_analyzer import parse_raw_news as _parse

    return _parse(title, content, source)

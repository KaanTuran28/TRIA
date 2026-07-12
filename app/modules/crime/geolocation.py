"""
Turkiye odakli sehir cikarma ve koordinat dogrulama.
"""

from __future__ import annotations

import re
from typing import Any

from app.modules.crime.services import CITY_COORDS, _normalize_city

# Yaklasik Turkiye sinir kutusu (deniz tamponu dahil)
TR_LAT_MIN, TR_LAT_MAX = 35.8, 42.4
TR_LON_MIN, TR_LON_MAX = 25.9, 44.8

# Ilce / bolge -> il (haber metninde gecen yaygin adlar)
DISTRICT_ALIASES: dict[str, str] = {
    "kadikoy": "istanbul",
    "kadıköy": "istanbul",
    "uskudar": "istanbul",
    "üsküdar": "istanbul",
    "besiktas": "istanbul",
    "beşiktaş": "istanbul",
    "sisli": "istanbul",
    "şişli": "istanbul",
    "beyoglu": "istanbul",
    "beyoğlu": "istanbul",
    "fatih": "istanbul",
    "bakirkoy": "istanbul",
    "bakırköy": "istanbul",
    "pendik": "istanbul",
    "kartal": "istanbul",
    "maltepe": "istanbul",
    "sultanbeyli": "istanbul",
    "cankaya": "ankara",
    "çankaya": "ankara",
    "kecioren": "ankara",
    "keçiören": "ankara",
    "yenimahalle": "ankara",
    "etimesgut": "ankara",
    "bornova": "izmir",
    "karsiyaka": "izmir",
    "karşıyaka": "izmir",
    "konak": "izmir",
    "buca": "izmir",
    "seyhan": "adana",
    "nilufer": "bursa",
    "nilüfer": "bursa",
    "osmangazi": "bursa",
    "antakya": "hatay",
    "diyarbakir": "diyarbakir",
    "gaziantep": "gaziantep",
}

# Yer adinda gecerse olay Turkiye disi sayilir (GDELT / haber)
FOREIGN_PLACE_MARKERS = (
    "netherlands",
    "hollanda",
    "syria",
    "suriye",
    "gaza",
    "israel",
    "israil",
    "iran",
    "irak",
    "iraq",
    "usa",
    "amerika",
    "united states",
    "russia",
    "rusya",
    "ukraine",
    "ukrayna",
    "germany",
    "almanya",
    "france",
    "fransa",
    "lebanon",
    "lubnan",
    "libya",
    "yemen",
    "afghanistan",
    "pakistan",
    "china",
    "cin ",
    "europe",
    "avrupa birligi",
    "palestine",
    "filistin",
    "egypt",
    "misir",
    "mısır",
    "greece",
    "yunanistan",
    "cyprus",
    "kibris",
    "kıbrıs",
)

DISASTER_CATEGORIES = frozenset(
    {
        "yangin",
        "yangın",
        "afet",
        "deprem",
        "sel",
        "heyelan",
        "hava",
        "meteoroloji",
    }
)

# Turkce karakterli sehir adlari -> CITY_COORDS anahtari
CITY_DISPLAY_NAMES: dict[str, str] = {
    "istanbul": "İstanbul",
    "izmir": "İzmir",
    "ankara": "Ankara",
    "antalya": "Antalya",
    "bursa": "Bursa",
    "adana": "Adana",
    "gaziantep": "Gaziantep",
    "diyarbakir": "Diyarbakır",
    "sanliurfa": "Şanlıurfa",
    "konya": "Konya",
    "trabzon": "Trabzon",
    "eskisehir": "Eskişehir",
    "mersin": "Mersin",
    "hatay": "Hatay",
    "samsun": "Samsun",
    "malatya": "Malatya",
    "van": "Van",
    "erzurum": "Erzurum",
}


def is_in_turkey(lat: float, lon: float) -> bool:
    return TR_LAT_MIN <= lat <= TR_LAT_MAX and TR_LON_MIN <= lon <= TR_LON_MAX


def _ascii_key(s: str) -> str:
    return (
        s.strip()
        .lower()
        .replace("i̇", "i")
        .replace("İ", "i")
        .replace("ı", "i")
        .replace("ğ", "g")
        .replace("ü", "u")
        .replace("ş", "s")
        .replace("ö", "o")
        .replace("ç", "c")
        .replace("â", "a")
        .replace("î", "i")
        .replace("û", "u")
    )


def _foreign_place(name: str) -> bool:
    n = _ascii_key(name)
    if "turkey" in n or "turkiye" in n or "türkiye" in name.lower():
        return False
    return any(m in n for m in FOREIGN_PLACE_MARKERS)


def extract_city_from_text(*texts: str) -> str | None:
    """Metinden Turkiye ili veya ilce adi cikar (en uzun eslesme oncelikli)."""
    blob = _ascii_key(" ".join(t for t in texts if t))

    found: list[tuple[int, str]] = []

    for city in sorted(CITY_COORDS.keys(), key=len, reverse=True):
        if re.search(rf"\b{re.escape(city)}\b", blob):
            found.append((len(city), city))

    for alias, city in sorted(DISTRICT_ALIASES.items(), key=lambda x: len(x[0]), reverse=True):
        key = _ascii_key(alias)
        if re.search(rf"\b{re.escape(key)}\b", blob):
            found.append((len(key), city))

    if not found:
        return None
    found.sort(reverse=True)
    return found[0][1]


def city_from_gdelt_place(place: str) -> str | None:
    """GDELT 'name' alanindan sehir; yabanci ulke ise None."""
    if not place:
        return None
    if _foreign_place(place):
        pl = place.lower()
        if "turkey" not in pl and "turkiye" not in _ascii_key(place):
            return None
    parts = re.split(r"[,/]", place)
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if _foreign_place(part):
            continue
        key = _ascii_key(part)
        if key in CITY_COORDS:
            return key
        if key in DISTRICT_ALIASES:
            return DISTRICT_ALIASES[key]
        for frag in ("istanbul", "ankara", "izmir", "turkey", "turkiye"):
            if frag in key and frag in CITY_COORDS:
                return frag
    return extract_city_from_text(place)


def normalize_category(raw: str | None) -> str | None:
    """
    Kategoriyi asayis setine indirger.
    Afet/yangin vb. icin None doner (silinmek uzere).
    """
    if not raw:
        return "asayis"
    c = _ascii_key(raw)
    if any(d in c for d in DISASTER_CATEGORIES):
        return None
    if "polis" in c or "jandarma" in c:
        return "polis"
    if "cinayet" in c or "katil" in c or "katl" in c or "oldur" in c:
        return "cinayet"
    if "teror" in c or "terör" in raw.lower():
        return "teror"
    if "operasyon" in c or "narkotik" in c or "uyusturucu" in c:
        return "operasyon"
    if "kaza" in c or "trafik" in c:
        return "kaza"
    if "gaspa" in c or "soygun" in c or "hirsiz" in c:
        return "hirsizlik"
    if "dolandir" in c:
        return "dolandiricilik"
    if "kavga" in c or "saldiri" in c or "saldırı" in raw.lower():
        return "saldiri"
    if "asayis" in c or "asayiş" in raw.lower():
        return "asayis"
    if c in ("suc", "suç", "suikast"):
        return "cinayet"
    return "asayis"


def derive_incident_type(category: str | None) -> str:
    """Kategoriden C4I olay sinifini turetir: crime | traffic_accident | fire_anomaly."""
    if not category:
        return "crime"
    c = _ascii_key(category)
    if "kaza" in c or "trafik" in c:
        return "traffic_accident"
    if any(d in c for d in DISASTER_CATEGORIES) or "patlama" in c or "anomali" in c:
        return "fire_anomaly"
    return "crime"


def resolve_crime_coordinates(
    *,
    title: str = "",
    body: str = "",
    city_hint: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
) -> dict[str, Any] | None:
    """
    Haber metnine gore Turkiye icinde lat/lon.
    Yabanci koordinat veya sehir bulunamazsa None.
    """
    city = _normalize_city(city_hint) if city_hint else None
    if city and city not in CITY_COORDS:
        city = None
    if not city:
        city = extract_city_from_text(title, body, city_hint or "")

    llm_in_turkey = (
        lat is not None
        and lon is not None
        and is_in_turkey(float(lat), float(lon))
    )

    if city and city in CITY_COORDS:
        c_lat, c_lon = CITY_COORDS[city]
        if llm_in_turkey:
            dist = abs(float(lat) - c_lat) + abs(float(lon) - c_lon)
            if dist < 2.5:
                return {
                    "city": city,
                    "lat": float(lat),
                    "lon": float(lon),
                    "geo_source": "llm_verified",
                }
        return {"city": city, "lat": c_lat, "lon": c_lon, "geo_source": "city_center"}

    if llm_in_turkey:
        guessed = extract_city_from_text(title, body)
        if guessed:
            c_lat, c_lon = CITY_COORDS[guessed]
            return {
                "city": guessed,
                "lat": c_lat,
                "lon": c_lon,
                "geo_source": "llm_bbox_city_fallback",
            }
        return {
            "city": None,
            "lat": float(lat),
            "lon": float(lon),
            "geo_source": "llm_bbox_only",
        }

    return None

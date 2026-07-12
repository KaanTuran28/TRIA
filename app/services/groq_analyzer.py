"""Groq LLM ile olay analizi ve AI Siddet Indeksi (1-10).

Token butcesi stratejisi:
- Sabit kurallar kisa bir SYSTEM mesajinda (her cagrida ayni, minimum token).
- Haber govdesi MAX_CONTENT_CHARS ile kirpilir (ilk paragraflar olayi tasir).
- JSON mode (response_format) ile ciktida gevezelik yok -> max_tokens dusuk.
- Ayni icerik hash'i tekrar gelirse LLM cagrisi atlanir (feed'ler arasi mukerrer haber).
"""

from __future__ import annotations

import ast
import hashlib
import json
import logging
import os
import re
from collections import OrderedDict
from typing import Any

from groq import Groq

from app.modules.crime.geolocation import derive_incident_type, normalize_category, resolve_crime_coordinates
from app.modules.crime.services import crime_prefilter_score, passes_crime_prefilter

logger = logging.getLogger(__name__)

MAX_CONTENT_CHARS = 1200   # haber govdesinden LLM'e giden azami karakter
MAX_OUTPUT_TOKENS = 220    # JSON cikti icin yeterli, gevezelige yer yok
LLM_CACHE_SIZE = 2000      # icerik-hash -> sonuc (mukerrer haberde token yakma)

SYSTEM_PROMPT = (
    "Turkiye asayis/suc/polis olay cikarici. Haberden TEK olay cikar, SADECE JSON don:\n"
    '{"is_crime":bool,"category":str,"severity_score":int,"description":str,"city":str,"confidence":float}\n'
    "severity_score 1-10 tam sayi: 1-2 kucuk olay; 3-4 hafif yaralanma/mala zarar; "
    "5-6 ciddi kaza/soygun; 7-8 silahli olay/operasyon; 9-10 cinayet/catisma/teror.\n"
    "Deprem/sel/hava durumu: is_crime=false. Yangin/patlama: is_crime=true, category=yangin.\n"
    "city: yalnizca Turkiye il adi, kucuk harf (istanbul, ankara...). Bilinmiyorsa bos birak.\n"
    "description: en fazla 160 karakter, kisisel veri (isim/plaka/TC) yazma."
)

# ---------------------------------------------------------------- LLM cache

_llm_cache: OrderedDict[str, dict[str, Any] | None] = OrderedDict()


def _content_key(title: str, content: str) -> str:
    return hashlib.sha256(f"{title}|{content[:400]}".encode()).hexdigest()[:32]


def _cache_get(key: str):
    if key in _llm_cache:
        _llm_cache.move_to_end(key)
        return True, _llm_cache[key]
    return False, None


def _cache_put(key: str, value: dict[str, Any] | None) -> None:
    _llm_cache[key] = value
    _llm_cache.move_to_end(key)
    while len(_llm_cache) > LLM_CACHE_SIZE:
        _llm_cache.popitem(last=False)


# ---------------------------------------------------------------- yardimcilar

def clamp_severity_score(value: Any) -> int:
    try:
        n = int(round(float(value)))
    except (TypeError, ValueError):
        n = 5
    return max(1, min(10, n))


def _client() -> Groq | None:
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        return None
    return Groq(api_key=api_key)


def _parse_llm_json(raw: str) -> dict[str, Any] | None:
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if not m:
        return None
    blob = m.group(0).strip()
    candidates = [
        blob,
        blob.replace("'", '"'),
        re.sub(r",\s*([}\]])", r"\1", blob),
        re.sub(r"\bTrue\b", "true", blob),
        re.sub(r"\bFalse\b", "false", blob),
        re.sub(r"\bNone\b", "null", blob),
    ]
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue
    try:
        parsed = ast.literal_eval(blob)
        if isinstance(parsed, dict):
            return parsed
    except (SyntaxError, ValueError):
        pass
    return None


def _heuristic_severity(title: str, content: str, category: str) -> int:
    text = f"{title} {content} {category}".lower()
    if any(k in text for k in ("olum", "oldur", "cinayet", "teror", "katliam")):
        return 9
    if any(k in text for k in ("silah", "bicak", "saldiri", "patlama")):
        return 8
    if any(k in text for k in ("agir yarali", "rehin", "kaciril")):
        return 7
    if any(k in text for k in ("hirsiz", "soygun", "gaspa")):
        return 6
    if any(k in text for k in ("kaza", "trafik", "devril")):
        return 5
    return 4


def _build_parsed_event(
    *,
    title: str,
    content: str,
    source: str,
    category: str,
    severity_score: int,
    description: str,
    city_hint: str | None,
    lat: float | None,
    lon: float | None,
    confidence: float,
) -> dict[str, Any] | None:
    cat = normalize_category(category)
    if cat is None:
        # Yangin/patlama C4I'da fire_anomaly olarak izlenir; diger afetler elenir.
        if derive_incident_type(category) != "fire_anomaly":
            return None
        cat = "afet"
    geo = resolve_crime_coordinates(
        title=title,
        body=content,
        city_hint=city_hint,
        lat=lat,
        lon=lon,
    )
    if not geo:
        logger.debug("Konum cozulemedi, olay atlandi: %s", title[:80])
        return None
    return {
        "category": cat,
        "severity_score": severity_score,
        "description": description[:2000],
        "city": geo["city"],
        "district": None,
        "lat": geo["lat"],
        "lon": geo["lon"],
        "confidence": confidence,
        "title": title[:500],
        "source": source,
    }


def _fallback_parse(title: str, content: str, source: str) -> dict[str, Any] | None:
    category = "asayis"
    sev = _heuristic_severity(title, content, category)
    return _build_parsed_event(
        title=title,
        content=content,
        source=source,
        category=category,
        severity_score=sev,
        description=title[:500],
        city_hint=None,
        lat=None,
        lon=None,
        confidence=0.35,
    )


# ---------------------------------------------------------------- ana giris

def parse_raw_news(title: str, content: str, source: str) -> dict[str, Any] | None:
    if not passes_crime_prefilter(title, content):
        return None

    # Mukerrer icerik: feed'ler arasi ayni haber icin LLM'i tekrar cagirma.
    key = _content_key(title, content)
    hit, cached = _cache_get(key)
    if hit:
        return dict(cached) if cached else None

    client = _client()
    if not client:
        result = _fallback_parse(title, content, source)
        _cache_put(key, result)
        return result

    model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    user_msg = f"Kaynak: {source}\nBaslik: {title}\nMetin: {content[:MAX_CONTENT_CHARS]}"
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.0,
            max_tokens=MAX_OUTPUT_TOKENS,
            response_format={"type": "json_object"},
        )
        raw = (resp.choices[0].message.content or "").strip()
        data = _parse_llm_json(raw)
        if not data:
            result = _fallback_parse(title, content, source)
            _cache_put(key, result)
            return result
        if data.get("is_crime") is False:
            _cache_put(key, None)
            return None

        pre_score = crime_prefilter_score(title, content)
        result = _build_parsed_event(
            title=title,
            content=content,
            source=source,
            category=str(data.get("category") or "asayis"),
            severity_score=clamp_severity_score(data.get("severity_score")),
            description=str(data.get("description") or title),
            city_hint=data.get("city"),
            lat=None,  # LLM koordinat tahmini istemiyoruz; geolocation cozumler
            lon=None,
            confidence=float(
                data.get("confidence") if data.get("confidence") is not None else pre_score
            ),
        )
        _cache_put(key, result)
        return result
    except Exception as exc:
        logger.warning("Groq parse hatasi: %s", exc)
        return _fallback_parse(title, content, source)

from app.services.groq_analyzer import _parse_llm_json, clamp_severity_score
from app.modules.crime.services import crime_prefilter_score, parse_raw_news


def test_crime_prefilter_detects_keywords():
    score = crime_prefilter_score("Silahli saldiri", "Ankara'da gasp olayi")
    assert score > 0.15


def test_clamp_severity_score_bounds():
    assert clamp_severity_score(0) == 1
    assert clamp_severity_score(15) == 10
    assert clamp_severity_score(7.4) == 7


def test_parse_llm_json_tolerates_trailing_commas():
    raw = '{"is_crime": true, "category": "kaza", "severity_score": 6.5,}'
    data = _parse_llm_json(raw)
    assert data is not None
    assert data["category"] == "kaza"


def test_parse_raw_news_fallback_without_api(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    result = parse_raw_news(
        "Ankara'da hirsizlik suphelisi yakalandi",
        "Polis ekipleri Ankara'da hirsizlik suphelisini yakaladi.",
        "test",
    )
    assert result is not None
    assert result["category"]

import os

import pytest

from app.modules.crime.alerts import get_alert_diagnostics, maybe_alert_high_risk_event
from app.modules.crime.services import crime_prefilter_score, parse_raw_news


def test_prefilter_detects_crime_text():
    assert crime_prefilter_score("Silahli saldiri Ankara", "Polis olay yerinde") >= 0.15


def test_groq_or_fallback_parse(monkeypatch):
    monkeypatch.setenv("CRIME_PREFILTER_THRESHOLD", "0.1")
    result = parse_raw_news(
        "Ankara'da hirsizlik suphelisi yakalandi",
        "Ankara Emniyet ekipleri hirsizlik suphelisini kisa surede yakaladi.",
        "test",
    )
    assert result is not None
    assert "severity_score" in result


def test_telegram_alert_threshold(monkeypatch):
    monkeypatch.setenv("TELEGRAM_GLOBAL_ALERTS_ENABLED", "0")
    low = maybe_alert_high_risk_event({"category": "asayis", "severity_score": 5.0})
    assert low["sent"] is False


def test_pipeline_diagnostics_import():
    from app.modules.crime.scraper import get_pipeline_diagnostics

    d = get_pipeline_diagnostics()
    assert "groq_configured" in d
    assert "rss_feed_count" in d
    assert "max_article_age_hours" in d
    assert "max_article_age_filter_active" in d


def test_prefilter_requires_keyword():
    from app.modules.crime.services import passes_crime_prefilter

    assert passes_crime_prefilter("Ekonomi bulteni", "Borsa yukseldi") is False
    assert passes_crime_prefilter("Ankara'da kaza", "Trafik kazasi 3 yarali") is True
    assert passes_crime_prefilter("Deprem oldu", "AFAD aciklama yapti") is False


def test_gdelt_severity_keywords():
    from app.scrapers.api_ingestor import gdelt_severity_from_text

    assert gdelt_severity_from_text("murder in Istanbul") >= 8
    assert gdelt_severity_from_text("police patrol district") == 5


def test_title_dedupe():
    from app.modules.crime.dedupe import is_duplicate_title

    known = ["Ankara'da silahli saldiri: 1 yarali"]
    assert is_duplicate_title("Ankara'da silahli saldiri 1 yarali", known) is True
    assert is_duplicate_title("Istanbul depremi", known) is False

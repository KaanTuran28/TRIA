from app.scrapers.api_ingestor import fetch_gdelt, gdelt_severity_from_text


def test_gdelt_severity_mapping():
    assert gdelt_severity_from_text("cinayet") == 9
    assert gdelt_severity_from_text("polis operasyon") == 5


def test_fetch_gdelt_disabled():
    assert fetch_gdelt({"enabled": False}) == []


def test_fetch_gdelt_parses_feature():
    from app.scrapers.api_ingestor import _feature_to_event

    feat = {
        "geometry": {"type": "Point", "coordinates": [32.85, 39.92]},
        "properties": {
            "name": "Ankara, Turkey",
            "url": "https://example.com/news/1",
            "mentionedthemes": ";ARREST;TAX_FNCACT_POLICE;",
        },
    }
    seen: set[str] = set()
    ev = _feature_to_event(feat, seen)
    assert ev is not None
    assert ev["category"] == "asayis"
    assert ev["lat"] == 39.92
    assert ev["severity_score"] >= 5


def test_fetch_gdelt_empty_url():
    assert fetch_gdelt({"enabled": True, "url": ""}) == []

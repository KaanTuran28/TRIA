"""Turkiye geolocation ve kategori normalizasyonu."""

from app.modules.crime.geolocation import (
    city_from_gdelt_place,
    extract_city_from_text,
    is_in_turkey,
    normalize_category,
    resolve_crime_coordinates,
)


def test_is_in_turkey():
    assert is_in_turkey(41.0, 29.0)
    assert not is_in_turkey(52.0, 5.0)


def test_normalize_category_disaster():
    assert normalize_category("Yangın") is None
    assert normalize_category("polis operasyonu") == "polis"


def test_extract_city_from_text():
    assert extract_city_from_text("Kadıköy'de polis operasyonu") == "istanbul"
    assert extract_city_from_text("Ankara'da cinayet") == "ankara"


def test_city_from_gdelt_foreign():
    assert city_from_gdelt_place("Amsterdam, Netherlands") is None
    assert city_from_gdelt_place("Istanbul, Turkey") == "istanbul"


def test_resolve_prefers_city_over_foreign_coords():
    geo = resolve_crime_coordinates(
        title="İstanbul'da operasyon",
        body="",
        lat=52.37,
        lon=4.89,
    )
    assert geo is not None
    assert geo["city"] == "istanbul"
    assert is_in_turkey(geo["lat"], geo["lon"])


def test_resolve_rejects_no_turkey_signal():
    assert (
        resolve_crime_coordinates(
            title="Netherlands court ruling",
            body="Amsterdam",
            lat=52.37,
            lon=4.89,
        )
        is None
    )

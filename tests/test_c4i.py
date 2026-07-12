"""C4I modulu birim testleri: rota ilerleme, dispatch, trend hesabi, IBB kayit esleme."""

from types import SimpleNamespace

from datetime import datetime, timedelta

from app.modules.c4i.coverage import compute_coverage_report, nearest_unit_distance
from app.modules.c4i.dispatch import eta_minutes, haversine_km, nearest_unit, priority_score
from app.modules.c4i.performance import (
    build_performance_report,
    compute_incident_durations,
    summarize_durations,
)
from app.modules.c4i.predictive import compute_predictive_score
from app.modules.c4i.router import _cache_get, _cache_put, pct_change
from app.modules.c4i.simulation import (
    _advance_along_route,
    _random_patrol_route,
    _route_arrived,
)
from app.modules.crime.geolocation import derive_incident_type
from app.modules.crime.population import POPULATION_2025, per_100k
from app.scrapers.ibb_ingestor import extract_incident


# ---------------------------------------------------------------- simulasyon

def test_patrol_route_is_closed_loop():
    route = _random_patrol_route(41.0, 29.0)
    assert len(route) >= 5
    assert route[0] == route[-1]  # kapali dongu


def test_advance_moves_along_route():
    route = {"waypoints": [[29.0, 41.0], [29.1, 41.0], [29.0, 41.0]], "leg": 0, "t": 0.0}
    new_route, lon, lat = _advance_along_route(route, speed_kmh=40.0, dt_s=3.0)
    assert lon > 29.0  # doguya ilerledi
    assert new_route["t"] > 0.0 or new_route["leg"] > 0


def test_patrol_route_wraps_around():
    # Cok kisa rota + yuksek hiz: bastan sarmali, patlamamali
    route = {"waypoints": [[29.0, 41.0], [29.0001, 41.0], [29.0, 41.0]], "leg": 0, "t": 0.0}
    new_route, lon, lat = _advance_along_route(route, speed_kmh=500.0, dt_s=60.0)
    assert 0 <= new_route["leg"] <= 1
    assert 28.9 < lon < 29.1


def test_dispatch_route_stops_at_target():
    route = {
        "waypoints": [[29.0, 41.0], [29.001, 41.0]],
        "leg": 0,
        "t": 0.0,
        "mode": "dispatch",
        "incident_id": 42,
    }
    new_route, lon, lat = _advance_along_route(route, speed_kmh=500.0, dt_s=600.0)
    assert new_route["t"] == 1.0
    assert abs(lon - 29.001) < 1e-9  # hedefte durdu, sarmadi
    assert _route_arrived(new_route)
    assert new_route["incident_id"] == 42  # mod bilgisi korunur


def test_route_not_arrived_midway():
    route = {"waypoints": [[29.0, 41.0], [30.0, 41.0]], "leg": 0, "t": 0.4, "mode": "dispatch"}
    assert not _route_arrived(route)


# ---------------------------------------------------------------- dispatch

def test_haversine_istanbul_ankara():
    km = haversine_km(41.0082, 28.9784, 39.9334, 32.8597)
    assert 340 < km < 360  # bilinen kus ucusu ~351 km


def test_nearest_unit_selection():
    units = [
        SimpleNamespace(id=1, unit_id="EKIP-34-01", lon=28.97, lat=41.00),
        SimpleNamespace(id=2, unit_id="EKIP-34-02", lon=29.20, lat=41.10),
    ]
    best, km = nearest_unit(units, lat=41.01, lon=28.98)
    assert best.id == 1
    assert km < 5


def test_nearest_unit_empty():
    best, km = nearest_unit([], lat=41.0, lon=29.0)
    assert best is None


def test_eta_minutes():
    assert eta_minutes(90.0, speed_kmh=90.0) == 60.0
    assert eta_minutes(0.0) == 0.0


def test_priority_score_severity_and_age():
    fresh = priority_score(severity=7.0, age_minutes=0.0)
    aged = priority_score(severity=7.0, age_minutes=30.0)
    assert aged > fresh  # starvation onleme: bekleyen olay oncelik kazanir
    assert fresh == 7.0


def test_priority_score_age_bonus_capped():
    capped = priority_score(severity=7.0, age_minutes=1000.0)
    assert capped == 10.0  # 7.0 + AGE_BONUS_CAP(3.0)


# ---------------------------------------------------------------- analitik

def test_pct_change_rules():
    assert pct_change(12, 8) == 50.0
    assert pct_change(4, 8) == -50.0
    assert pct_change(5, 0) == 100.0  # onceki donem bos
    assert pct_change(0, 0) == 0.0


def test_analytics_cache_roundtrip():
    _cache_put("test:key", {"a": 1})
    assert _cache_get("test:key") == {"a": 1}
    assert _cache_get("test:missing") is None


# ---------------------------------------------------------------- incident_type

def test_derive_incident_type():
    assert derive_incident_type("kaza") == "traffic_accident"
    assert derive_incident_type("trafik") == "traffic_accident"
    assert derive_incident_type("yangin") == "fire_anomaly"
    assert derive_incident_type("patlama") == "fire_anomaly"
    assert derive_incident_type("cinayet") == "crime"
    assert derive_incident_type(None) == "crime"


# ---------------------------------------------------------------- IBB ingestor

IBB_KAZA = {
    "_id": 148194,
    "ANNOUNCEMENT_ID": 999001,
    "ANNOUNCEMENT_TYPE_DESC": "Kaza Bildirimi",
    "ANNOUNCEMENT_TITLE": "TEM Istoc-Mahmutbey Yonu trafik kazasi (yaralanmali)",
    "ANNOUNCEMENT_STARTING_DATETIME": "2025-03-05T13:27:00",
    "LATITUDE": 41.05,
    "LONGITUDE": 28.83,
}


def test_ibb_extract_kaza():
    inc = extract_incident(IBB_KAZA)
    assert inc is not None
    assert inc["incident_type"] == "traffic_accident"
    assert inc["category"] == "kaza"
    assert inc["severity_score"] == 6.0  # "yaralanmali" -> 6
    assert inc["city"] == "istanbul"
    assert inc["source_url"] == "ibb://trafik/999001"
    assert inc["timestamp"].year == 2025


def test_ibb_extract_skips_maintenance():
    rec = dict(IBB_KAZA, ANNOUNCEMENT_TYPE_DESC="Bakım-Onarım Çalışması")
    assert extract_incident(rec) is None


def test_ibb_extract_skips_bad_coords():
    rec = dict(IBB_KAZA, LATITUDE=None)
    assert extract_incident(rec) is None
    rec2 = dict(IBB_KAZA, LATITUDE=10.0)  # Turkiye disi
    assert extract_incident(rec2) is None


def test_ibb_severity_hasarli_default():
    rec = dict(IBB_KAZA, ANNOUNCEMENT_TITLE="D100 trafik kazasi (hasarli)")
    inc = extract_incident(rec)
    assert inc["severity_score"] == 4.0


# ---------------------------------------------------------------- nufus normalizasyonu

def test_population_covers_all_81_provinces():
    from app.modules.crime.services import CITY_COORDS

    assert len(POPULATION_2025) == 81
    assert set(POPULATION_2025) == set(CITY_COORDS)


def test_per_100k_calculation():
    # istanbul nufusu ~15.75M; 1575 olay ~10.0/100k civari olmali
    result = per_100k(1575, "istanbul")
    assert 9.5 < result < 10.5


def test_per_100k_unknown_city():
    assert per_100k(10, "bilinmeyen_sehir") is None


# ---------------------------------------------------------------- prediktif risk

def test_predictive_score_high_intensity_and_trend():
    scored = compute_predictive_score(
        recent_count=10, recent_hours=3.0,
        baseline_count=20, baseline_hours=24.0 * 28,
        avg_severity_recent=8.0, trend_pct=60.0,
    )
    assert scored["risk_level"] in ("high", "critical")
    assert scored["intensity_ratio"] > 1.0


def test_predictive_score_quiet_city():
    scored = compute_predictive_score(
        recent_count=0, recent_hours=3.0,
        baseline_count=0, baseline_hours=24.0 * 28,
        avg_severity_recent=0.0, trend_pct=0.0,
    )
    assert scored["predictive_score"] == 0.0
    assert scored["risk_level"] == "low"


def test_predictive_score_bounded_0_100():
    scored = compute_predictive_score(
        recent_count=1000, recent_hours=1.0,
        baseline_count=1, baseline_hours=24.0 * 28,
        avg_severity_recent=10.0, trend_pct=1000.0,
    )
    assert 0.0 <= scored["predictive_score"] <= 100.0


# ---------------------------------------------------------------- performans KPI

def _event(ts, dispatched=None, arrived=None, resolved=None, city="istanbul", unit="EKIP-34-01"):
    return SimpleNamespace(
        timestamp=ts, dispatched_at=dispatched, arrived_at=arrived,
        resolved_at=resolved, city=city, assigned_unit_id=unit,
    )


def test_compute_incident_durations_full_chain():
    t0 = datetime(2026, 1, 1, 10, 0, 0)
    row = _event(
        t0,
        dispatched=t0 + timedelta(minutes=2),
        arrived=t0 + timedelta(minutes=7),
        resolved=t0 + timedelta(minutes=20),
    )
    d = compute_incident_durations(row)
    assert d["dispatch_delay_min"] == 2.0
    assert d["travel_time_min"] == 5.0
    assert d["onscene_duration_min"] == 13.0
    assert d["total_response_min"] == 20.0


def test_compute_incident_durations_partial_chain():
    t0 = datetime(2026, 1, 1, 10, 0, 0)
    row = _event(t0, dispatched=t0 + timedelta(minutes=3))  # henuz varmadi/kapanmadi
    d = compute_incident_durations(row)
    assert d["dispatch_delay_min"] == 3.0
    assert d["travel_time_min"] is None
    assert d["onscene_duration_min"] is None
    assert d["total_response_min"] is None


def test_summarize_durations_basic_stats():
    s = summarize_durations([10.0, 20.0, 30.0])
    assert s["avg"] == 20.0
    assert s["median"] == 20.0
    assert s["min"] == 10.0
    assert s["max"] == 30.0
    assert s["count"] == 3


def test_summarize_durations_empty():
    s = summarize_durations([])
    assert s["count"] == 0
    assert s["avg"] is None


def test_build_performance_report_aggregates_by_city_and_unit():
    t0 = datetime(2026, 1, 1, 10, 0, 0)
    rows = [
        _event(t0, dispatched=t0 + timedelta(minutes=1), arrived=t0 + timedelta(minutes=5),
               resolved=t0 + timedelta(minutes=15), city="istanbul", unit="EKIP-34-01"),
        _event(t0, dispatched=t0 + timedelta(minutes=2), arrived=t0 + timedelta(minutes=8),
               resolved=t0 + timedelta(minutes=25), city="istanbul", unit="EKIP-34-02"),
        _event(t0, dispatched=t0 + timedelta(minutes=1)),  # henuz cozulmedi -> genel istatistige girmez
    ]
    report = build_performance_report(rows)
    assert report["sample_size"] == 3
    assert report["resolved_count"] == 2
    assert report["by_city"][0]["city"] == "istanbul"
    assert report["by_city"][0]["count"] == 2
    assert len(report["by_unit"]) == 2


# ---------------------------------------------------------------- kapsama boslugu

def test_nearest_unit_distance_picks_closest():
    units = [(41.10, 29.10), (41.00, 29.00)]
    d = nearest_unit_distance(41.001, 29.001, units)
    assert d < 1.0  # ikinci birime cok yakin


def test_nearest_unit_distance_no_units_penalty():
    from app.modules.c4i.coverage import NO_COVERAGE_PENALTY_KM

    assert nearest_unit_distance(41.0, 29.0, []) == NO_COVERAGE_PENALTY_KM


def test_coverage_report_flags_far_incidents():
    incidents = [
        {"city": "sirnak", "lat": 37.5, "lon": 42.5, "severity_score": 9.0},
        {"city": "sirnak", "lat": 37.5, "lon": 42.5, "severity_score": 8.0},
        {"city": "istanbul", "lat": 41.0, "lon": 29.0, "severity_score": 6.0},
    ]
    units = [{"lat": 41.001, "lon": 29.001}]  # yalnizca istanbul yakininda birim var
    report = compute_coverage_report(incidents, units)
    assert report["gaps"][0]["city"] == "sirnak"  # en uzak/yogun bolge en yuksek skor
    assert report["gaps"][0]["avg_distance_km"] > 100
    istanbul_gap = next(g for g in report["gaps"] if g["city"] == "istanbul")
    assert istanbul_gap["avg_distance_km"] < 1.0


def test_coverage_report_empty_incidents():
    report = compute_coverage_report([], [{"lat": 41.0, "lon": 29.0}])
    assert report["gaps"] == []
    assert report["incident_count"] == 0

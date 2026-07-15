from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_optional_user, require_admin, scope_city_for, scope_district_for
from app.core.database import get_db
from app.modules.audit.service import log_audit
from app.modules.crime.geojson_utils import rows_to_feature_collection
from app.modules.crime.models import CrimeEvent, RawNewsArchive
from app.modules.crime.schemas import CrimeStatsResponse
from app.modules.crime.services import parse_raw_news
from app.modules.crime.scraper import (
    get_pipeline_diagnostics,
    get_scraper_metrics,
    is_scraper_running,
    run_news_scraper_bot,
)
from app.modules.crime.data_cleanup import normalize_crime_database
from app.modules.crime.sources_config import get_sources_summary, reload_sources_config
router = APIRouter(tags=["Suç Haritası"])

_MAP_INDEX = Path(__file__).resolve().parents[3] / "frontend" / "templates" / "index.html"


@router.get("/", include_in_schema=False)
async def home():
    return RedirectResponse(url="/admin")


@router.get("/map", include_in_schema=False)
async def crime_map_page():
    return FileResponse(_MAP_INDEX, media_type="text/html")


@router.get("/geojson")
async def crime_geojson(
    days: int = Query(default=90, ge=1, le=730, description="Son N gunun olaylari"),
    limit: int = Query(default=5000, ge=100, le=20000),
    city: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: dict | None = Depends(get_optional_user),
):
    """city_operator/ilce_amiri oturumu varsa yalnizca kendi il/ilcesine ait olaylar dondurulur
    (zorunlu kisitlama)."""
    scope_city = scope_city_for(user)
    scope_district = scope_district_for(user)
    if scope_city:
        city = scope_city
    since = datetime.utcnow() - timedelta(days=days)
    conditions = [CrimeEvent.location.isnot(None), CrimeEvent.timestamp >= since]
    if city:
        conditions.append(func.lower(CrimeEvent.city) == city.strip().lower())
    if scope_district:
        conditions.append(func.lower(CrimeEvent.district) == scope_district.strip().lower())
    rows = (
        await db.execute(
            select(
                CrimeEvent.id,
                CrimeEvent.category,
                CrimeEvent.incident_type,
                CrimeEvent.severity_score,
                CrimeEvent.description,
                CrimeEvent.source,
                CrimeEvent.city,
                CrimeEvent.district,
                CrimeEvent.timestamp,
                CrimeEvent.source_url,
                CrimeEvent.resolved_at,
                func.ST_X(CrimeEvent.location).label("lon"),
                func.ST_Y(CrimeEvent.location).label("lat"),
            )
            .where(*conditions)
            .order_by(CrimeEvent.timestamp.desc())
            .limit(limit)
        )
    ).all()
    return rows_to_feature_collection(rows)


@router.get("/stats", response_model=CrimeStatsResponse)
async def crime_stats(db: AsyncSession = Depends(get_db), user: dict | None = Depends(get_optional_user)):
    scope_city = scope_city_for(user)
    base_filter = [func.lower(CrimeEvent.city) == scope_city] if scope_city else []
    total = (
        await db.execute(select(func.count()).select_from(CrimeEvent).where(*base_filter))
    ).scalar_one()
    cat_rows = (
        await db.execute(
            select(CrimeEvent.category, func.count())
            .where(*base_filter)
            .group_by(CrimeEvent.category)
            .order_by(func.count().desc())
        )
    ).all()
    metrics = get_scraper_metrics()
    return CrimeStatsResponse(
        total_events=int(total or 0),
        categories={str(c or "diger"): int(n) for c, n in cat_rows},
        last_scraper_run=metrics.get("last_run_at"),
    )


@router.post("/scrape")
async def trigger_scraper(background_tasks: BackgroundTasks):
    if is_scraper_running():
        return {"status": "already_running"}
    background_tasks.add_task(run_news_scraper_bot)
    return {"status": "started", "message": "Haber taramasi baslatildi."}


@router.post("/ingest/ibb", dependencies=[Depends(require_admin)])
async def trigger_ibb_ingest():
    """IBB Acik Veri trafik duyurularini hemen cek (resmi kaynak)."""
    from app.scrapers.ibb_ingestor import run_ibb_ingest

    return await run_ibb_ingest()


@router.get("/ingest/ibb/metrics")
async def ibb_ingest_metrics():
    from app.scrapers.ibb_ingestor import INGEST_METRICS

    return INGEST_METRICS


@router.get("/scraper/metrics")
async def scraper_metrics():
    return {
        "running": is_scraper_running(),
        **get_scraper_metrics(),
    }


@router.get("/pipeline/diagnostics")
async def pipeline_diagnostics():
    return get_pipeline_diagnostics()


@router.get("/sources")
async def list_sources():
    """Aktif tarama kaynaklari (config/sources.json)."""
    return get_sources_summary()


@router.post("/sources/reload", dependencies=[Depends(require_admin)])
async def reload_sources():
    """Kaynak dosyasini yeniden oku (degisiklik sonrasi)."""
    reload_sources_config()
    return {"status": "ok", **get_sources_summary()}


@router.post("/test/groq", dependencies=[Depends(require_admin)])
async def test_groq_pipeline():
    title = "Istanbul'da silahli saldiri: 1 yarali"
    body = (
        "Istanbul Besiktas'ta silahli saldiri meydana geldi. "
        "Olay yerine polis ve ambulans sevk edildi. Yaralinin durumunun agir oldugu bildirildi."
    )
    parsed = parse_raw_news(title, body, "test_groq")
    return {"ok": parsed is not None, "parsed": parsed}


@router.post("/normalize-data", dependencies=[Depends(require_admin)])
async def normalize_data(db: AsyncSession = Depends(get_db)):
    """Kategorileri ve Turkiye disi koordinatlari duzeltir."""
    stats = await normalize_crime_database(db)
    return {"status": "ok", **stats}


@router.post("/clear", dependencies=[Depends(require_admin)])
async def clear_data(db: AsyncSession = Depends(get_db), user: dict | None = Depends(get_optional_user)):
    await db.execute(delete(CrimeEvent))
    await db.execute(delete(RawNewsArchive))
    await db.commit()
    await log_audit(db, user, "data.clear")
    return {"message": "Tum suc verileri silindi."}



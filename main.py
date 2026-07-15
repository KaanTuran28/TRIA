import os
from contextlib import asynccontextmanager
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.modules.crime.spatial import router as spatial_router
from app.core.database import AsyncSessionLocal, Base, engine
from app.core.logging_config import configure_logging
from app.modules.auth.models import User  # noqa: F401
from app.modules.auth.router import router as auth_router
from app.modules.auth.seed import seed_demo_users
from app.modules.c4i.models import PoliceUnit  # noqa: F401
from app.modules.c4i.router import router as c4i_router
from app.modules.c4i.simulation import (
    HISTORY_SNAPSHOT_INTERVAL_S,
    TICK_SECONDS,
    seed_police_units,
    simulation_tick,
    snapshot_unit_history,
)
from app.modules.crime.models import CrimeEvent, RawNewsArchive  # noqa: F401
from app.modules.crime.router import router as map_router
from app.modules.crime.scraper import run_news_scraper_bot
from app.modules.crime.sources_config import get_official_api_config
from app.scrapers.ibb_ingestor import run_ibb_ingest
from app.ui.admin import router as admin_router
from app.ui.login import router as login_router

PROJECT_ROOT = Path(__file__).resolve().parent
FRONTEND_STATIC = PROJECT_ROOT / "frontend" / "static"

configure_logging()
scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Hafif migration: mevcut kurulumlara incident_type kolonunu ekle + geriye donuk doldur.
        await conn.execute(
            text("ALTER TABLE crime_events ADD COLUMN IF NOT EXISTS incident_type VARCHAR NOT NULL DEFAULT 'crime'")
        )
        await conn.execute(
            text(
                "UPDATE crime_events SET incident_type = 'traffic_accident' "
                "WHERE incident_type = 'crime' AND (category ILIKE '%kaza%' OR category ILIKE '%trafik%')"
            )
        )
        # Demo/test verileri kaldirildi (v2.1): eski demo kayitlarini da temizle.
        await conn.execute(
            text(
                "DELETE FROM crime_events WHERE source = 'demo_presentation' "
                "OR source_url LIKE 'demo://%'"
            )
        )
        # Not: timestamp/severity indeksleri artik CrimeEvent.__table_args__ uzerinden
        # yonetiliyor (create_all + Alembic ortak kaynak) — bkz. app/modules/crime/models.py

    # C4I: devriye birimlerini hazirla ve simulasyonu baslat
    async with AsyncSessionLocal() as db:
        await seed_police_units(db)
    async with AsyncSessionLocal() as db:
        await seed_demo_users(db)
    scheduler.add_job(simulation_tick, "interval", seconds=TICK_SECONDS, id="c4i_patrol_sim", max_instances=1)
    scheduler.add_job(
        snapshot_unit_history, "interval", seconds=HISTORY_SNAPSHOT_INTERVAL_S,
        id="c4i_history_snapshot", max_instances=1,
    )

    if os.getenv("RUN_SCAN_ON_STARTUP", "0").strip() in {"1", "true", "yes"}:
        scheduler.add_job(run_news_scraper_bot, "interval", minutes=60, id="scraper")

    # Resmi veri: IBB trafik duyurulari (sources.json > official_apis ile kontrol edilir)
    ibb_cfg = get_official_api_config("ibb_trafik_duyuru")
    if ibb_cfg.get("enabled") is True:
        interval = int(ibb_cfg.get("interval_minutes") or 30)
        scheduler.add_job(run_ibb_ingest, "interval", minutes=interval, id="ibb_ingest", max_instances=1)

    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(
    title="TRIA C4I — Gerçek Zamanlı Kolluk İstihbarat Ağı",
    description="OSINT olay füzyonu + canlı devriye takibi + prediktif risk analitiği (C4I ortak harekat resmi)",
    version="2.4.0",
    docs_url="/api/docs",
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(GZipMiddleware, minimum_size=1024)  # GeoJSON yanitlari ~10x kuculur
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

if FRONTEND_STATIC.is_dir():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_STATIC)), name="static")

app.include_router(admin_router)
app.include_router(login_router)
app.include_router(map_router)
app.include_router(spatial_router)
app.include_router(c4i_router)
app.include_router(auth_router)


@app.get("/health", tags=["Sistem"])
async def health():
    return {"status": "ok", "service": "tria-c4i-network"}

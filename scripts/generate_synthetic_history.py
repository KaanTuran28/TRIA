"""Sentetik cok-yillik gecmis crime_events verisi uretir/temizler.

Amac: seasonal.py/predictive.py'nin docstring'lerindeki "gercek mevsimsellik icin birden
fazla yilin verisi gerekir" notunu ELINDE veriyle test edebilmek — gercek OSINT/ihbar
verisi su an yalnizca birkac ay kapsiyor (bkz. CLAUDE.md). Uretilen kayitlar acikca
source="synthetic_history" ile etiketlenir ve --clear ile tek komutla geri temizlenebilir;
canli demo veritabanini kalici olarak degistirmez.

Guvenlik notu: tum zaman damgalari en az 60 gun oncesine ayarlanir (varsayilan islem
pencereleri — trends/scorecard/dispatch/coverage 7-30 gunluk pencereler kullanir) ve
resolved_at hemen doldurulur, boylece bu kayitlar aktif operasyonel gorunumleri (sevk
kuyrugu, kapsama boslugu, 7g trend) ETKILEMEZ — yalnizca seasonal.py gibi tum-zamanlarli
sorgulayan analizlerde gorunur.

Kullanim (docker container icinden, DATABASE_URL 'database' hostname'ine gore ayarli oldugu icin):
    docker exec tria_app python scripts/generate_synthetic_history.py --years 2
    docker exec tria_app python scripts/generate_synthetic_history.py --clear
"""

from __future__ import annotations

import argparse
import asyncio
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import delete, func, select  # noqa: E402

from app.core.database import AsyncSessionLocal  # noqa: E402
from app.modules.crime.models import CrimeEvent  # noqa: E402
from app.modules.crime.services import CITY_COORDS  # noqa: E402

SOURCE_TAG = "synthetic_history"
SAFE_WINDOW_DAYS = 60  # bu esikten daha yeni sentetik kayit uretilmez (bkz. modul docstring'i)

# Kategori -> (aylik taban olay sayisi, ay->carpan agirlik haritasi, incident_type)
# "kapkap" bilinctli olarak net bir yaz artisi gostersin diye tasarlandi (seasonal.py'nin
# is_summer_riser mantigini test eder); "hirsizlik" kontrol grubu olarak duz/mevsimsiz.
CATEGORY_PROFILES: dict[str, dict] = {
    "hirsizlik": {"base": 10, "weights": {}, "incident_type": "crime"},  # duz dagilim (kontrol grubu)
    "kapkac": {
        "base": 4, "incident_type": "crime",
        "weights": {6: 2.2, 7: 2.6, 8: 2.3},  # yaz artisi
    },
    "gasp": {
        "base": 3, "incident_type": "crime",
        "weights": {11: 1.6, 12: 1.8, 1: 1.7, 2: 1.4},  # kis artisi
    },
    "trafik kazasi": {
        "base": 6, "incident_type": "traffic_accident",
        "weights": {6: 1.6, 7: 1.9, 8: 1.7},  # yaz tatili yol trafigi
    },
}

DEMO_CITIES = ["istanbul", "ankara", "izmir", "amasya", "diyarbakir", "antalya"]


def _month_weight(profile: dict, month: int) -> float:
    return profile["weights"].get(month, 1.0)


def _random_point_near(lat: float, lon: float) -> tuple[float, float]:
    return lat + random.uniform(-0.08, 0.08), lon + random.uniform(-0.08, 0.08)


async def clear_synthetic(db) -> int:
    result = await db.execute(delete(CrimeEvent).where(CrimeEvent.source == SOURCE_TAG))
    await db.commit()
    return result.rowcount or 0


async def generate(db, years: int, cities: list[str]) -> int:
    now = datetime.utcnow()
    oldest = now - timedelta(days=365 * years)
    newest = now - timedelta(days=SAFE_WINDOW_DAYS)
    created = 0

    cursor = oldest.replace(day=1)
    while cursor < newest:
        month = cursor.month
        for city in cities:
            coords = CITY_COORDS.get(city)
            if not coords:
                continue
            base_lat, base_lon = coords
            for category, profile in CATEGORY_PROFILES.items():
                n = max(0, round(profile["base"] * _month_weight(profile, month) * random.uniform(0.8, 1.2)))
                for _ in range(n):
                    day = random.randint(1, 28)
                    hour = random.randint(0, 23)
                    ts = cursor.replace(day=day, hour=hour, minute=random.randint(0, 59))
                    if ts >= newest:
                        continue
                    lat, lon = _random_point_near(base_lat, base_lon)
                    db.add(
                        CrimeEvent(
                            category=category,
                            incident_type=profile["incident_type"],
                            severity_score=round(random.uniform(2.0, 8.0), 1),
                            description=None,
                            source=SOURCE_TAG,
                            city=city,
                            district=None,
                            location=f"SRID=4326;POINT({lon} {lat})",
                            timestamp=ts,
                            resolved_at=ts + timedelta(minutes=random.randint(15, 90)),
                            required_units=1,
                            assigned_unit_ids=[],
                        )
                    )
                    created += 1
        # bir sonraki aya gec
        cursor = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1)

    await db.commit()
    return created


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=2, help="Kac yillik gecmis veri uretilsin (varsayilan 2)")
    parser.add_argument("--cities", type=str, default=",".join(DEMO_CITIES), help="Virgulle ayrilmis il listesi")
    parser.add_argument("--clear", action="store_true", help="Uretmek yerine mevcut sentetik kayitlari sil")
    args = parser.parse_args()

    async with AsyncSessionLocal() as db:
        if args.clear:
            deleted = await clear_synthetic(db)
            print(f"Silindi: {deleted} sentetik kayit (source='{SOURCE_TAG}').")
            return 0

        existing = (
            await db.execute(select(func.count()).select_from(CrimeEvent).where(CrimeEvent.source == SOURCE_TAG))
        ).scalar_one()
        if existing:
            print(f"Zaten {existing} sentetik kayit var — once --clear ile temizleyin.")
            return 1

        cities = [c.strip().lower() for c in args.cities.split(",") if c.strip()]
        created = await generate(db, args.years, cities)
        print(f"Uretildi: {created} sentetik olay ({args.years} yil, {len(cities)} il, source='{SOURCE_TAG}').")
        print("Temizlemek icin: python scripts/generate_synthetic_history.py --clear")
        return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

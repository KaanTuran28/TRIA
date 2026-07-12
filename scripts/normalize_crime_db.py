"""Mevcut crime_events kayitlarini normalize eder (kategori + Turkiye konumu)."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.database import AsyncSessionLocal
from app.modules.crime.data_cleanup import normalize_crime_database


async def main() -> int:
    async with AsyncSessionLocal() as db:
        stats = await normalize_crime_database(db)
    print("Normalize tamamlandi:", stats)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

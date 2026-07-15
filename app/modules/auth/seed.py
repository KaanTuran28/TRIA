"""Demo kullanici tohumlama — tablo bossa calisir (bkz. simulation.py > seed_police_units deseni).

Gercek kurumsal devreye alista bu hesaplarin sifreleri degistirilmeli / kaldirilmalidir.
"""

from __future__ import annotations

import logging
import os

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User
from app.modules.auth.security import hash_password

logger = logging.getLogger("tria.auth.seed")

# (username, role, city, district, display_name, sifre-env-degiskeni, varsayilan sifre)
_DEMO_ACCOUNTS = [
    ("admin", "admin", None, None, "Genel Yönetici", "DEMO_ADMIN_PASSWORD", "admin123"),
    ("amasya_asayis", "city_operator", "amasya", None, "Amasya İl Asayiş Yönetimi", "DEMO_AMASYA_PASSWORD", "amasya123"),
    ("istanbul_asayis", "city_operator", "istanbul", None, "İstanbul İl Asayiş Yönetimi", "DEMO_ISTANBUL_PASSWORD", "istanbul123"),
    ("merzifon_amirlik", "ilce_amiri", "amasya", "Merzifon", "Merzifon İlçe Emniyet Amirliği", "DEMO_MERZIFON_PASSWORD", "merzifon123"),
    ("merkez", "merkez", None, None, "EGM Merkez İzleme (Salt Okunur)", "DEMO_MERKEZ_PASSWORD", "merkez123"),
]


async def seed_demo_users(db: AsyncSession) -> int:
    existing = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    if existing:
        return 0

    created = 0
    for username, role, city, district, display_name, env_key, default_pw in _DEMO_ACCOUNTS:
        password = os.getenv(env_key, default_pw)
        db.add(
            User(
                username=username,
                password_hash=hash_password(password),
                role=role,
                city=city,
                district=district,
                display_name=display_name,
            )
        )
        created += 1
    await db.commit()
    logger.info("Auth: %s demo kullanici olusturuldu (sifreleri .env'den DEMO_*_PASSWORD ile ozellestirilebilir)", created)
    return created

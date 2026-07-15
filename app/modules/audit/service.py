"""log_audit() — tum yazma islemlerinin tek ortak kayit noktasi."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditLog


async def log_audit(
    db: AsyncSession,
    user: dict | None,
    action: str,
    *,
    resource_type: str | None = None,
    resource_id: str | None = None,
    city: str | None = None,
    detail: str | None = None,
) -> None:
    """Bir yazma islemini denetim kaydina ekler ve hemen commit eder (kendi kucuk islemi).

    user None ise (yalnizca X-Admin-Key ile yapilan sistem-geneli islem) actor "admin_key"
    olarak isaretlenir — gercek bir kullanici hesabina baglanmadigi acikca belli olsun diye.
    """
    db.add(
        AuditLog(
            username=(user or {}).get("sub") or "admin_key",
            role=(user or {}).get("role") or "admin_key",
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            city=city,
            detail=detail,
        )
    )
    await db.commit()

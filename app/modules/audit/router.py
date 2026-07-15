"""Denetim kaydi sorgulama — yalnizca admin (bkz. app/modules/audit/service.py > log_audit)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_admin
from app.core.database import get_db
from app.modules.audit.models import AuditLog

router = APIRouter(prefix="/api/v1", tags=["Audit"])


@router.get("/audit-log", dependencies=[Depends(require_admin)])
async def list_audit_log(
    action: str | None = Query(default=None),
    city: str | None = Query(default=None),
    username: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    conditions = []
    if action:
        conditions.append(AuditLog.action == action)
    if city:
        conditions.append(AuditLog.city == city.strip().lower())
    if username:
        conditions.append(AuditLog.username == username.strip().lower())
    rows = (
        await db.execute(
            select(AuditLog)
            .where(*conditions)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    return {
        "count": len(rows),
        "entries": [
            {
                "id": r.id, "username": r.username, "role": r.role, "action": r.action,
                "resource_type": r.resource_type, "resource_id": r.resource_id,
                "city": r.city, "detail": r.detail, "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ],
    }

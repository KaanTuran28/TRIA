import os

from fastapi import Header, HTTPException, status


async def require_admin(x_admin_key: str | None = Header(default=None, alias="X-Admin-Key")) -> None:
    expected = os.getenv("ADMIN_API_KEY", "").strip()
    if not expected:
        return
    if not x_admin_key or x_admin_key.strip() != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Gecersiz veya eksik X-Admin-Key.",
        )

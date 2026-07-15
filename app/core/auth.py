import os

from fastapi import Depends, Header, HTTPException, status

from app.modules.auth.security import verify_token


async def get_optional_user(authorization: str | None = Header(default=None)) -> dict | None:
    """Authorization: Bearer <token> varsa dogrular, yoksa/gecersizse None doner (401 atmaz)."""
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    return verify_token(token)


def scope_city_for(user: dict | None) -> str | None:
    """city_operator icin kendi ilini, admin/anonim icin None (kisitlama yok) dondurur."""
    if user and user.get("role") == "city_operator":
        return (user.get("city") or "").strip().lower() or None
    return None


async def require_admin(
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
    user: dict | None = Depends(get_optional_user),
) -> None:
    """Sistem-genelinde admin islemleri: gecerli admin-rolu token VEYA (varsa) X-Admin-Key.

    ADMIN_API_KEY ayarlanmamissa (gelistirme kolayligi icin) ve gecerli bir token da yoksa
    eskisi gibi acik birakilir — bu davranis degistirilmedi, sadece token yolu eklendi.
    """
    if user and user.get("role") == "admin":
        return
    expected = os.getenv("ADMIN_API_KEY", "").strip()
    if not expected:
        return
    if not x_admin_key or x_admin_key.strip() != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Gecersiz veya eksik X-Admin-Key (ya da admin girisi gerekli).",
        )


async def require_login(user: dict | None = Depends(get_optional_user)) -> dict:
    """Herhangi bir gecerli oturum (admin veya city_operator) gerektirir."""
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Giriş gerekli.")
    return user


async def require_write_access(
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
    user: dict | None = Depends(get_optional_user),
) -> dict | None:
    """Ihbar girisi / olay kapatma gibi sehir-operasyonel yazma islemleri.

    Admin (rol veya X-Admin-Key) her ile yazabilir; city_operator sadece kendi iline
    (asil sehir karsilastirmasi endpoint icinde scope_city_for ile yapilir). Gecerli
    oturum/anahtar yoksa (ve ADMIN_API_KEY ayarliysa) 401 doner.
    """
    if user and user.get("role") in ("admin", "city_operator"):
        return user
    expected = os.getenv("ADMIN_API_KEY", "").strip()
    if not expected:
        return None
    if not x_admin_key or x_admin_key.strip() != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Giriş veya X-Admin-Key gerekli.")
    return None

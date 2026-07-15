"""Giris/oturum API'si — sehir bazli asayis yonetimi hesaplari icin."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_optional_user
from app.core.database import get_db
from app.modules.auth.models import User
from app.modules.auth.security import sign_token, verify_password

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


def _user_public(user: User) -> dict:
    return {
        "username": user.username,
        "role": user.role,
        "city": user.city,
        "display_name": user.display_name,
    }


@router.post("/login")
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    username = payload.username.strip().lower()
    user = (await db.execute(select(User).where(User.username == username))).scalar_one_or_none()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Kullanıcı adı veya şifre hatalı.")
    token = sign_token({"sub": user.username, "role": user.role, "city": user.city})
    return {"token": token, **_user_public(user)}


@router.get("/me")
async def me(user: dict | None = Depends(get_optional_user)):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Oturum yok.")
    return {"username": user.get("sub"), "role": user.get("role"), "city": user.get("city")}

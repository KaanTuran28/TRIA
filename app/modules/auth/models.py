"""Kullanici modeli: sehir bazli asayis yonetimi hesaplari.

role="admin" -> city=None, tum illeri/ilceleri gorur ve tum islemleri yapabilir.
role="city_operator" -> city="amasya" gibi, yalnizca kendi iline gorunum/yazma yetkisi var
(bkz. app/core/auth.py > get_optional_user + router'lardaki scope_city kullanimi).
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from app.core.database import Base

USER_ROLES = ("admin", "city_operator")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default="city_operator")
    city = Column(String, nullable=True, index=True)  # None ise admin (tum iller)
    display_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

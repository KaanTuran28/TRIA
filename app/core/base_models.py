from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer

from app.core.database import Base


class RiskEventMixin:
    id = Column(Integer, primary_key=True, index=True)
    severity_score = Column(Float, nullable=False, default=5.0)  # AI Siddet Indeksi 1-10
    timestamp = Column(DateTime, nullable=True, default=datetime.utcnow)

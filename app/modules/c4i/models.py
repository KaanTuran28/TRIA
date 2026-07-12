"""C4I modeli: gercek zamanli kolluk kuvveti (devriye) takibi."""

from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import Column, DateTime, Float, Integer, String
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base

UNIT_STATUSES = ("patrolling", "responding", "offline")


class PoliceUnit(Base):
    __tablename__ = "police_units"

    id = Column(Integer, primary_key=True, index=True)
    unit_id = Column(String, unique=True, index=True, nullable=False)  # ör. "EKIP-34-01"
    unit_type = Column(String, nullable=False, default="patrol_car")  # patrol_car | motorcycle | swat
    status = Column(String, nullable=False, default="patrolling", index=True)
    city = Column(String, nullable=True, index=True)
    current_location = Column(Geometry(geometry_type="POINT", srid=4326), nullable=True)
    # {"waypoints": [[lon, lat], ...], "leg": 0, "t": 0.0} — devriye rotasi + ilerleme durumu
    assigned_route = Column(JSONB, nullable=True)
    speed_kmh = Column(Float, nullable=False, default=40.0)
    last_update = Column(DateTime, nullable=True, default=datetime.utcnow)


class PoliceUnitHistory(Base):
    """Birim konum gecmisi — periyodik anlik goruntu (iz surme / sonradan analiz icin)."""

    __tablename__ = "police_unit_history"

    id = Column(Integer, primary_key=True, index=True)
    unit_id = Column(String, index=True, nullable=False)
    status = Column(String, nullable=False)
    location = Column(Geometry(geometry_type="POINT", srid=4326), nullable=True)
    speed_kmh = Column(Float, nullable=True)
    recorded_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

"""C4I modeli: gercek zamanli kolluk kuvveti (devriye) takibi."""

from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base

UNIT_STATUSES = ("patrolling", "responding", "offline")

# Asayis birim tipleri (il/ilce asayis yonetiminin gercek devriye siniflandirmasi).
# "patrol_car"/"motorcycle" eski degerler geriye donuk uyumluluk icin destekleniyor
# (frontend ikon eslemesinde varsayilana duser).
UNIT_TYPES = ("asayis", "trafik", "tem", "yunus", "cevik_kuvvet")

UNIT_TYPE_LABELS_TR = {
    "asayis": "Asayiş",
    "trafik": "Trafik",
    "tem": "TEM (Terörle Mücadele)",
    "yunus": "Yunus Timi",
    "cevik_kuvvet": "Çevik Kuvvet",
    "patrol_car": "Asayiş",
    "motorcycle": "Yunus Timi",
}


class PoliceUnit(Base):
    __tablename__ = "police_units"

    id = Column(Integer, primary_key=True, index=True)
    unit_id = Column(String, unique=True, index=True, nullable=False)  # ör. "EKIP-34-01"
    unit_type = Column(String, nullable=False, default="asayis")  # bkz. UNIT_TYPES
    status = Column(String, nullable=False, default="patrolling", index=True)
    city = Column(String, nullable=True, index=True)
    district = Column(String, nullable=True, index=True)  # ilce (ör. "Merzifon")
    current_location = Column(Geometry(geometry_type="POINT", srid=4326), nullable=True)
    # {"waypoints": [[lon, lat], ...], "leg": 0, "t": 0.0} — devriye rotasi + ilerleme durumu
    assigned_route = Column(JSONB, nullable=True)
    speed_kmh = Column(Float, nullable=False, default=40.0)
    last_update = Column(DateTime, nullable=True, default=datetime.utcnow)


SHIFTS = ("gunduz", "gece")  # 08:00-20:00 / 20:00-08:00 (TRT, UTC+3)


class Personnel(Base):
    """Devriye personeli — birim basina vardiya (gunduz/gece) atamasi.

    Salt-okunur raporlama katmanidir: dispatch/simulasyon mantigini etkilemez, yalnizca
    "hangi birimde kim, hangi vardiyada gorevli" sorusuna cevap verir (bkz. CLAUDE.md v2.9).
    """

    __tablename__ = "personnel"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    sicil_no = Column(String, unique=True, index=True, nullable=False)
    rank = Column(String, nullable=False, default="Polis Memuru")
    unit_id = Column(String, index=True, nullable=True)  # PoliceUnit.unit_id (gevsek referans)
    shift = Column(String, nullable=False, default="gunduz")  # bkz. SHIFTS
    city = Column(String, nullable=True, index=True)
    district = Column(String, nullable=True, index=True)
    active = Column(Boolean, nullable=False, default=True)


class PoliceUnitHistory(Base):
    """Birim konum gecmisi — periyodik anlik goruntu (iz surme / sonradan analiz icin)."""

    __tablename__ = "police_unit_history"

    id = Column(Integer, primary_key=True, index=True)
    unit_id = Column(String, index=True, nullable=False)
    status = Column(String, nullable=False)
    location = Column(Geometry(geometry_type="POINT", srid=4326), nullable=True)
    speed_kmh = Column(Float, nullable=True)
    recorded_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

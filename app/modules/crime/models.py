from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import Column, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from app.core.base_models import RiskEventMixin
from app.core.database import Base


class CrimeEvent(Base, RiskEventMixin):
    __tablename__ = "crime_events"

    category = Column(String, index=True)
    # C4I olay sinifi: crime | traffic_accident | fire_anomaly
    incident_type = Column(String, nullable=False, default="crime", server_default="crime", index=True)
    description = Column(Text, nullable=True)
    source = Column(String)
    city = Column(String, nullable=True, index=True)
    location = Column(Geometry(geometry_type="POINT", srid=4326), nullable=True)
    source_url = Column(String, nullable=True, index=True)
    extra_data = Column(JSONB, nullable=True)
    # Dispatch is akisi: birim atandiginda assigned_unit_id + dispatched_at dolar,
    # olay yerine varildiginda arrived_at, mudahale tamamlaninca resolved_at dolar.
    # Bu uc zaman damgasi performans KPI'larinin (sevk gecikmesi/seyahat/sahne suresi) temelidir.
    assigned_unit_id = Column(String, nullable=True, index=True)
    dispatched_at = Column(DateTime, nullable=True)
    arrived_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_crime_events_timestamp", "timestamp"),
        Index("ix_crime_events_ts_sev", "timestamp", "severity_score"),
    )


class RawNewsArchive(Base):
    __tablename__ = "raw_news_archive"

    id = Column(Integer, primary_key=True, index=True)
    source_url = Column(String, unique=True, index=True)
    title = Column(String, nullable=True)
    content_hash = Column(String, nullable=True, index=True)
    fetched_at = Column(DateTime, default=datetime.utcnow)

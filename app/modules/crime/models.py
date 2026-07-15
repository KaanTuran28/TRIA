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
    district = Column(String, nullable=True, index=True)  # ilce (ör. "Merzifon") — su an sadece manuel ihbar girisinde dolar
    location = Column(Geometry(geometry_type="POINT", srid=4326), nullable=True)
    source_url = Column(String, nullable=True, index=True)
    extra_data = Column(JSONB, nullable=True)
    # Dispatch is akisi: birim atandiginda assigned_unit_id + dispatched_at dolar,
    # olay yerine varildiginda arrived_at, mudahale tamamlaninca resolved_at dolar.
    # Bu uc zaman damgasi performans KPI'larinin (sevk gecikmesi/seyahat/sahne suresi) temelidir.
    assigned_unit_id = Column(String, nullable=True, index=True)  # ilk (birincil) atanan birim — geriye donuk uyumluluk
    dispatched_at = Column(DateTime, nullable=True)
    arrived_at = Column(DateTime, nullable=True)  # ilk birimin varis zamani
    resolved_at = Column(DateTime, nullable=True)  # TUM birimler isini bitirince dolar (coklu-birim sevk)
    # Coklu-birim sevk (v2.6): cok yuksek siddetli olaylar (bkz. dispatch.py > compute_required_units)
    # birden fazla birim gerektirir. assigned_unit_ids KUMULATIF'tir (bu olaya sevk edilmis TUM
    # birimlerin listesi, asla eksiltilmez) — auto_dispatch "kac birim daha gerekli" hesabini bu
    # listenin uzunluguna gore yapar. Cozum (resolved_at), o an fiilen sahada/yolda baska birim
    # kalmadiginda dolar (bkz. simulation.py > simulation_tick, in-memory "others_active" kontrolu).
    required_units = Column(Integer, nullable=False, default=1, server_default="1")
    assigned_unit_ids = Column(JSONB, nullable=True)

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

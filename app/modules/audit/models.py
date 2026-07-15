"""Denetim kaydi (audit log) — kim ne zaman hangi yazma islemini yapti.

Dis entegrasyon gerektirmez, KVKK'ya hazirlik olarak sistem-ici islemleri kayit altina alir
(bkz. CLAUDE.md v2.9). Gercek kurumsal devreye alista bu tabloya bir saklama/silme politikasi
(retention policy) eklenmelidir — su an sinirsiz birikiyor.
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, nullable=True, index=True)
    role = Column(String, nullable=True)
    action = Column(String, nullable=False, index=True)  # ör. "incident.report", "auth.login"
    resource_type = Column(String, nullable=True)
    resource_id = Column(String, nullable=True)
    city = Column(String, nullable=True, index=True)
    detail = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

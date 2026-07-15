"""Eskalasyon tespiti — cozulmemis/eksik-birim atanmis kritik olaylar icin in-app uyari.

Gercek SMS/push bildirim kanali yok (Telegram v2.6'da kaldirildi) — bu, kurum-agnostik bir
"sistem ici uyari panosu" (bkz. CLAUDE.md v2.9). Saf fonksiyon: DB'den bagimsiz test edilebilir,
mevcut coverage.py/scorecard.py deseniyle ayni ruhta.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

UNRESOLVED_THRESHOLD_MIN = 20.0  # bu sureden uzun suredir acik kalan kritik olay -> eskalasyon
UNDERSTAFFED_THRESHOLD_MIN = 10.0  # coklu-birim gerektirip hala eksik atanmissa (bkz. dispatch.py)


def compute_escalations(incidents: list[dict[str, Any]], now: datetime | None = None) -> list[dict[str, Any]]:
    """Cozulmemis kritik olaylardan eskalasyon geregi olanlari secip nedenleriyle dondurur.

    incidents: {"id","city","district","severity_score","timestamp","required_units",
    "assigned_unit_ids"} alanlarini iceren (zaten resolved_at IS NULL ile filtrelenmis) liste.
    """
    now = now or datetime.utcnow()
    rows = []
    for inc in incidents:
        age_min = (now - inc["timestamp"]).total_seconds() / 60.0
        assigned = inc.get("assigned_unit_ids") or []
        required = inc.get("required_units") or 1

        reasons = []
        if age_min > UNRESOLVED_THRESHOLD_MIN:
            reasons.append("gecikmis_mudahale")
        if required > len(assigned) and age_min > UNDERSTAFFED_THRESHOLD_MIN:
            reasons.append("eksik_birim")
        if not reasons:
            continue

        rows.append(
            {
                "id": inc["id"],
                "city": inc.get("city"),
                "district": inc.get("district"),
                "severity_score": inc.get("severity_score"),
                "age_minutes": round(age_min, 1),
                "required_units": required,
                "assigned_count": len(assigned),
                "reasons": reasons,
                "escalation_score": round((inc.get("severity_score") or 0.0) + age_min / 10.0, 1),
            }
        )

    rows.sort(key=lambda r: r["escalation_score"], reverse=True)
    return rows

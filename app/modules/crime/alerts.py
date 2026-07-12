import json
import logging
import os
import time
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

_last_global_alert_at = 0.0


def _telegram_configured() -> bool:
    return bool(os.getenv("TELEGRAM_BOT_TOKEN", "").strip() and os.getenv("TELEGRAM_CHAT_ID", "").strip())


def _alerts_enabled() -> bool:
    return os.getenv("TELEGRAM_GLOBAL_ALERTS_ENABLED", "0").strip().lower() in {"1", "true", "yes"}


def _min_severity() -> float:
    return float(os.getenv("TELEGRAM_ALERT_MIN_SEVERITY", "7.0"))


def _category_allowed(category: str | None) -> bool:
    allow = os.getenv("TELEGRAM_ALERT_CATEGORY_ALLOWLIST", "").strip()
    if not allow:
        return True
    allowed = {c.strip().lower() for c in allow.split(",") if c.strip()}
    return (category or "asayis").strip().lower() in allowed


def _cooldown_seconds() -> int:
    return int(os.getenv("TELEGRAM_GLOBAL_COOLDOWN_MINUTES", "3") or "3") * 60


def send_telegram_message(text: str) -> dict[str, Any]:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        return {"ok": False, "error": "TELEGRAM_BOT_TOKEN veya TELEGRAM_CHAT_ID eksik"}
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": text[:4000]}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        return {"ok": bool(body.get("ok")), "response": body}
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")
        return {"ok": False, "error": f"HTTP {exc.code}", "detail": err_body[:500]}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def maybe_alert_high_risk_event(parsed: dict[str, Any], *, source_url: str = "") -> dict[str, Any]:
    """Yuksek riskli olaylari Telegram'a gonderir (cooldown + esik)."""
    global _last_global_alert_at
    if not _alerts_enabled() or not _telegram_configured():
        return {"sent": False, "reason": "telegram_disabled"}
    sev = float(parsed.get("severity_score") or 0)
    if sev < _min_severity():
        return {"sent": False, "reason": "below_severity_threshold", "severity": sev}
    if not _category_allowed(parsed.get("category")):
        return {"sent": False, "reason": "category_not_allowed"}
    now = time.time()
    if now - _last_global_alert_at < _cooldown_seconds():
        return {"sent": False, "reason": "cooldown"}
    text = (
        "TRIA — Yuksek risk olayi\n"
        f"Kategori: {parsed.get('category', '-')}\n"
        f"Seviye: {sev}/10\n"
        f"Sehir: {parsed.get('city') or '-'}\n"
        f"{(parsed.get('description') or '')[:350]}\n"
        f"Kaynak: {parsed.get('source', '-')}\n"
        f"{source_url[:200] if source_url else ''}"
    )
    result = send_telegram_message(text)
    if result.get("ok"):
        _last_global_alert_at = now
        return {"sent": True, "severity": sev}
    return {"sent": False, "reason": "send_failed", **result}


def get_alert_diagnostics() -> dict[str, Any]:
    return {
        "telegram_configured": _telegram_configured(),
        "alerts_enabled": _alerts_enabled(),
        "min_severity": _min_severity(),
        "cooldown_minutes": _cooldown_seconds() // 60,
        "category_allowlist": os.getenv("TELEGRAM_ALERT_CATEGORY_ALLOWLIST", ""),
    }

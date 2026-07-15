"""Sifre hash'leme ve oturum token'i — harici JWT/passlib bagimliligi olmadan (stdlib).

Token formati: base64(json payload) + "." + base64(HMAC-SHA256 imza) — kucuk olcekli bir
platform icin yeterli, ekstra pip bagimliligi + Docker yeniden build'i gerektirmiyor.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time

PBKDF2_ITERATIONS = 200_000
TOKEN_TTL_SECONDS = 12 * 60 * 60  # 12 saat — vardiya suresi


def _secret_key() -> bytes:
    return os.getenv("AUTH_SECRET_KEY", "tria-dev-insecure-secret-change-me").encode()


def _b64e(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return f"{_b64e(salt)}${_b64e(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_b64, digest_b64 = stored.split("$", 1)
        salt, expected = _b64d(salt_b64), _b64d(digest_b64)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


def sign_token(payload: dict) -> str:
    body = {**payload, "exp": time.time() + TOKEN_TTL_SECONDS}
    raw = json.dumps(body, separators=(",", ":")).encode()
    sig = hmac.new(_secret_key(), raw, hashlib.sha256).digest()
    return f"{_b64e(raw)}.{_b64e(sig)}"


def verify_token(token: str) -> dict | None:
    try:
        raw_b64, sig_b64 = token.split(".", 1)
        raw = _b64d(raw_b64)
        expected_sig = hmac.new(_secret_key(), raw, hashlib.sha256).digest()
        if not hmac.compare_digest(expected_sig, _b64d(sig_b64)):
            return None
        payload = json.loads(raw)
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None

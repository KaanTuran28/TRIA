"""URL ve baslik benzerligi ile deduplikasyon."""

from __future__ import annotations

import os
import re
import unicodedata


def _normalize_text(text: str) -> str:
    t = unicodedata.normalize("NFKD", text.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def title_shingles(title: str, k: int = 3) -> set[str]:
    words = _normalize_text(title).split()
    if not words:
        return set()
    if len(words) < k:
        return {" ".join(words)}
    return {" ".join(words[i : i + k]) for i in range(len(words) - k + 1)}


def jaccard_similarity(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def similarity_threshold() -> float:
    return float(os.getenv("CONTENT_SIMILARITY_THRESHOLD", "0.8"))


def is_duplicate_title(title: str, known_titles: list[str]) -> bool:
    """Baslik Jaccard benzerligi esigi uzerindeyse duplicate say."""
    shingles = title_shingles(title)
    if not shingles:
        return False
    threshold = similarity_threshold()
    for other in known_titles:
        if jaccard_similarity(shingles, title_shingles(other)) >= threshold:
            return True
    return False

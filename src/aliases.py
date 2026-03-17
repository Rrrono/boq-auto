"""Alias loading and application helpers."""

from __future__ import annotations

import re

from .models import AliasEntry
from .normalizer import normalize_text


def apply_aliases(text: str, aliases: list[AliasEntry]) -> tuple[str, list[AliasEntry]]:
    """Replace known aliases in normalized text and return alias hits."""
    normalized = normalize_text(text)
    hits: list[AliasEntry] = []
    for entry in aliases:
        alias = normalize_text(entry.alias)
        canonical = normalize_text(entry.canonical_term)
        if not alias or alias not in normalized:
            continue
        normalized = re.sub(rf"\b{re.escape(alias)}\b", canonical, normalized)
        hits.append(entry)
    return normalized, hits

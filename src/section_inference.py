"""Infer BOQ sections from sheet names and heading context."""

from __future__ import annotations

import re

from .models import BOQLine, SectionRule
from .normalizer import normalize_text

SHEET_SECTION_HINTS = {
    "preliminaries": "Preliminaries",
    "dayworks": "Dayworks",
    "contractor equipment": "Dayworks",
    "contractor s equipment": "Dayworks",
    "contractors equipment": "Dayworks",
    "plant": "Dayworks",
    "plant hire": "Dayworks",
    "earthworks": "Earthworks",
    "concrete": "Concrete",
    "general items": "Preliminaries",
    "finishes": "Finishes",
}


def classify_sheet_name(sheet_name: str) -> str:
    """Infer a likely section from a messy worksheet title."""
    normalized = normalize_text(sheet_name)
    normalized = re.sub(r"\bbill no\b", "bill", normalized)
    for hint, section in SHEET_SECTION_HINTS.items():
        if hint in normalized:
            return section
    return ""


def infer_section(sheet_name: str, row: BOQLine, nearby_headings: list[str], rules: list[SectionRule]) -> str:
    """Infer a section by applying trigger rules to sheet and heading context."""
    sheet_hint = classify_sheet_name(sheet_name)
    context = [sheet_name, sheet_hint, *nearby_headings[-5:], row.description]
    corpus = normalize_text(" ".join(part for part in context if part))
    for rule in sorted(rules, key=lambda item: item.priority, reverse=True):
        trigger = normalize_text(rule.trigger_text)
        if trigger and trigger in corpus:
            return rule.inferred_section
    return sheet_hint

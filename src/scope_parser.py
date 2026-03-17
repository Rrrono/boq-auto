"""Scope parsing for tender-analysis workflows."""

from __future__ import annotations

import logging

from .models import AppConfig
from .tender_models import ScopeSection, TenderDocument


SECTION_LABELS = {
    "preliminaries": "Preliminaries",
    "earthworks": "Earthworks",
    "concrete": "Concrete",
    "finishes": "Finishes",
    "plumbing": "Plumbing",
    "drainage": "Drainage",
    "electrical": "Electrical",
    "external_works": "External Works",
    "dayworks": "Dayworks",
    "contractors_equipment": "Contractor's Equipment",
    "provisional_items": "Provisional Items",
}


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def _looks_like_heading(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    return stripped.isupper() or stripped.endswith(":") or len(stripped.split()) <= 6


class ScopeParser:
    """Infer likely tender scope sections from tender text."""

    def __init__(self, config: AppConfig, logger: logging.Logger | None = None) -> None:
        self.config = config
        self.logger = logger
        self.keywords: dict[str, list[str]] = config.get("tender_analysis.scope_section_keywords", {})

    def parse(self, document: TenderDocument) -> list[ScopeSection]:
        bucket: dict[str, ScopeSection] = {}
        for line in document.lines:
            normalized_line = _normalize(line.text)
            for section_key, keywords in self.keywords.items():
                matched = [keyword for keyword in keywords if keyword.lower() in normalized_line]
                if not matched:
                    continue
                label = SECTION_LABELS.get(section_key, section_key.replace("_", " ").title())
                entry = bucket.setdefault(label, ScopeSection(section_name=label, confidence=0.0))
                if line.source_reference not in entry.source_references:
                    entry.source_references.append(line.source_reference)
                for keyword in matched:
                    if keyword not in entry.matched_keywords:
                        entry.matched_keywords.append(keyword)
                score = 58.0 + min(len(matched) * 10.0, 20.0)
                if _looks_like_heading(line.text):
                    score += 10.0
                entry.confidence = min(max(entry.confidence, score), 95.0)

        sections = sorted(bucket.values(), key=lambda item: (-item.confidence, item.section_name))
        if self.logger:
            self.logger.info("Parsed %s tender scope section(s).", len(sections))
        return sections

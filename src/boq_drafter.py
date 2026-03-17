"""Draft BOQ suggestion generation from tender analysis outputs."""

from __future__ import annotations

import logging

from .models import AppConfig
from .normalizer import normalize_text
from .tender_models import DraftBOQSuggestion, ScopeSection, TenderDocument


def _clean_line_text(text: str) -> str:
    return text.strip().lstrip("-").strip().rstrip(":").strip()


class BOQDrafter:
    """Generate review-first draft BOQ suggestions from tender text."""

    def __init__(self, config: AppConfig, logger: logging.Logger | None = None) -> None:
        self.config = config
        self.logger = logger
        raw_units: dict[str, str] = config.get("tender_analysis.draft_units", {})
        self.config_units = {
            normalize_text(key).replace(" ", "_"): str(value)
            for key, value in raw_units.items()
        }

    def build_suggestions(self, document: TenderDocument, scope_sections: list[ScopeSection]) -> list[DraftBOQSuggestion]:
        suggestions: list[DraftBOQSuggestion] = []
        seen: set[tuple[str, str]] = set()

        for section in scope_sections:
            section_lines = [
                line for line in document.lines if any(reference == line.source_reference for reference in section.source_references)
            ]
            if not section_lines:
                suggestions.append(self._section_placeholder(section))
                continue

            for line in section_lines:
                description = _clean_line_text(line.text)
                if not description or len(description.split()) < 2:
                    continue
                signature = (section.section_name, normalize_text(description))
                if signature in seen:
                    continue
                seen.add(signature)
                suggestions.append(
                    DraftBOQSuggestion(
                        section=section.section_name,
                        description=description,
                        unit=self._suggest_unit(section.section_name, description),
                        quantity_placeholder="TBD",
                        rate_placeholder="Rate to be built/priced",
                        amount_placeholder="Derived after measurement",
                        source_basis=f"Tender text matched via {', '.join(section.matched_keywords)}",
                        source_reference=line.source_reference,
                        confidence=max(55.0, min(section.confidence, 88.0)),
                        notes="Draft BOQ suggestion only. Quantity must be measured or confirmed.",
                    )
                )

        if self.logger:
            self.logger.info("Built %s draft BOQ suggestion(s).", len(suggestions))
        return suggestions

    def _section_placeholder(self, section: ScopeSection) -> DraftBOQSuggestion:
        return DraftBOQSuggestion(
            section=section.section_name,
            description=f"Insert BOQ line items for {section.section_name.lower()} based on tender text.",
            unit=self._suggest_unit(section.section_name, section.section_name),
            quantity_placeholder="TBD",
            rate_placeholder="Rate to be built/priced",
            amount_placeholder="Derived after measurement",
            source_basis=f"Scope section inferred from keywords: {', '.join(section.matched_keywords)}",
            source_reference=", ".join(section.source_references),
            confidence=max(50.0, min(section.confidence - 5.0, 80.0)),
            notes="Section-level placeholder because no clear line-item wording was found.",
        )

    def _suggest_unit(self, section_name: str, description: str) -> str:
        lowered = description.lower()
        normalized_section = normalize_text(section_name).replace(" ", "_")
        if normalized_section in self.config_units:
            return str(self.config_units[normalized_section])
        if any(token in lowered for token in {"excavation", "concrete", "backfill"}):
            return "m3"
        if any(token in lowered for token in {"paint", "plaster", "tiling", "screed"}):
            return "m2"
        if any(token in lowered for token in {"fence", "pipe", "cabling"}):
            return "m"
        if any(token in lowered for token in {"manhole", "light", "pump", "visit"}):
            return "nr"
        return "item"

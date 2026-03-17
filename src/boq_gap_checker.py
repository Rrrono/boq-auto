"""Review-first BOQ gap checking against tender scope."""

from __future__ import annotations

import logging

from .models import AppConfig
from .normalizer import normalize_text
from .section_inference import classify_sheet_name
from .tender_models import BOQGapItem, DraftBOQSuggestion, ScopeSection
from .workbook_reader import WorkbookReader


class BOQGapChecker:
    """Compare tender scope and draft suggestions against an optional BOQ workbook."""

    def __init__(self, config: AppConfig, logger: logging.Logger | None = None) -> None:
        self.config = config
        self.logger = logger
        self.reader = WorkbookReader(config, logger)

    def check(
        self,
        tender_scope: list[ScopeSection],
        draft_suggestions: list[DraftBOQSuggestion],
        boq_path: str | None = None,
    ) -> list[BOQGapItem]:
        if not boq_path:
            return self._build_review_only_scope_gaps(tender_scope, draft_suggestions)

        sheets = self.reader.read(boq_path)
        boq_sections: dict[str, list[str]] = {}
        for sheet in sheets:
            sheet_section = classify_sheet_name(sheet.sheet_name) or sheet.sheet_name
            descriptions = [normalize_text(row.description) for row in sheet.rows if row.description and not row.is_summary_row]
            boq_sections.setdefault(sheet_section, []).extend(descriptions)

        gaps: list[BOQGapItem] = []

        for section in tender_scope:
            section_name = section.section_name
            existing = boq_sections.get(section_name, [])
            if not existing:
                gaps.append(
                    BOQGapItem(
                        gap_type="Missing Section",
                        section=section_name,
                        description=f"Tender scope indicates section '{section_name}' but no equivalent BOQ section was detected.",
                        source_reference=", ".join(section.source_references),
                        confidence=max(55.0, min(section.confidence, 82.0)),
                        notes="Review-first finding. Confirm whether the BOQ omits this section or uses a different label.",
                    )
                )

        for suggestion in draft_suggestions:
            section_descriptions = boq_sections.get(suggestion.section, [])
            normalized_suggestion = normalize_text(suggestion.description)
            if any(normalized_suggestion in existing or existing in normalized_suggestion for existing in section_descriptions if existing):
                continue
            gaps.append(
                BOQGapItem(
                    gap_type="Missing Item",
                    section=suggestion.section,
                    description=suggestion.description,
                    source_reference=suggestion.source_reference,
                    confidence=max(50.0, min(suggestion.confidence, 78.0)),
                    notes="Suggested tender-derived item was not clearly located in the supplied BOQ. Review manually.",
                )
            )

        for suggestion in draft_suggestions:
            if "tbd" not in suggestion.quantity_placeholder.lower():
                continue
            if "provisional" in suggestion.description.lower() or "dayworks" in suggestion.description.lower():
                gaps.append(
                    BOQGapItem(
                        gap_type="Measurement Clarification",
                        section=suggestion.section,
                        description=suggestion.description,
                        source_reference=suggestion.source_reference,
                        confidence=62.0,
                        notes="Item still requires measurement or tender confirmation before pricing.",
                    )
                )

        if self.logger:
            self.logger.info("Built %s BOQ gap finding(s).", len(gaps))
        return gaps

    def _build_review_only_scope_gaps(
        self,
        tender_scope: list[ScopeSection],
        draft_suggestions: list[DraftBOQSuggestion],
    ) -> list[BOQGapItem]:
        gaps: list[BOQGapItem] = []
        for section in tender_scope:
            gaps.append(
                BOQGapItem(
                    gap_type="Scope Review",
                    section=section.section_name,
                    description="No BOQ workbook supplied. Confirm whether this tender scope section should appear in the draft BOQ.",
                    source_reference=", ".join(section.source_references),
                    confidence=max(50.0, min(section.confidence, 75.0)),
                    notes="Review-only gap because no BOQ was provided for comparison.",
                )
            )
        for suggestion in draft_suggestions[:10]:
            gaps.append(
                BOQGapItem(
                    gap_type="Draft Review",
                    section=suggestion.section,
                    description=suggestion.description,
                    source_reference=suggestion.source_reference,
                    confidence=max(50.0, min(suggestion.confidence, 72.0)),
                    notes="Review whether this suggested line should be added to the working BOQ.",
                )
            )
        return gaps

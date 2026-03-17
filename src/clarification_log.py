"""Clarification logging for tender-analysis workflows."""

from __future__ import annotations

import logging

from .models import AppConfig
from .tender_models import ClarificationEntry, ScopeSection, TenderDocument, TenderRequirement


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


class ClarificationLogBuilder:
    """Build a practical clarification queue from tender text and extracted results."""

    def __init__(self, config: AppConfig, logger: logging.Logger | None = None) -> None:
        self.config = config
        self.logger = logger
        self.patterns: dict[str, list[str]] = config.get("tender_analysis.clarification_keywords", {})

    def build(
        self,
        document: TenderDocument,
        requirements: list[TenderRequirement],
        scope_sections: list[ScopeSection],
    ) -> list[ClarificationEntry]:
        entries: list[ClarificationEntry] = []
        seen: set[tuple[str, str]] = set()

        for line in document.lines:
            normalized_line = _normalize(line.text)
            for category, patterns in self.patterns.items():
                if not any(pattern in normalized_line for pattern in patterns):
                    continue
                signature = (category, line.source_reference)
                if signature in seen:
                    continue
                seen.add(signature)
                entries.append(
                    ClarificationEntry(
                        clarification_id=f"CL-{len(entries) + 1:03d}",
                        category=category.replace("_", " ").title(),
                        description=line.text,
                        source_reference=line.source_reference,
                        confidence=68.0,
                        action_needed=self._action_for(category),
                        notes="Tender wording may require clarification before pricing or submission.",
                    )
                )

        for requirement in requirements:
            if not requirement.review_flag:
                continue
            signature = ("requirement_review", requirement.source_reference)
            if signature in seen:
                continue
            seen.add(signature)
            entries.append(
                ClarificationEntry(
                    clarification_id=f"CL-{len(entries) + 1:03d}",
                    category="Requirement Review",
                    description=requirement.description,
                    source_reference=requirement.source_reference,
                    confidence=max(55.0, min(requirement.confidence, 80.0)),
                    action_needed="Confirm the exact tender requirement and record the response route.",
                    notes=requirement.notes or "Human review required before hand-off.",
                )
            )

        for section in scope_sections:
            if section.confidence >= 70:
                continue
            signature = ("scope_section", section.section_name)
            if signature in seen:
                continue
            seen.add(signature)
            entries.append(
                ClarificationEntry(
                    clarification_id=f"CL-{len(entries) + 1:03d}",
                    category="Unclear Scope",
                    description=f"Scope section '{section.section_name}' is weakly inferred from the tender text.",
                    source_reference=", ".join(section.source_references),
                    confidence=section.confidence,
                    action_needed="Confirm whether this section should appear in the BOQ or tender scope tracker.",
                    notes="Low-confidence scope inference.",
                )
            )

        if self.logger:
            self.logger.info("Built %s clarification log entries.", len(entries))
        return entries

    @staticmethod
    def _action_for(category: str) -> str:
        if category == "unclear_scope":
            return "Confirm the intended scope wording and BOQ treatment."
        if category == "missing_measurements":
            return "Request missing dimensions, quantities, or measurement rules."
        if category == "conflicting_instructions":
            return "Resolve the conflicting instruction before submission or pricing."
        return "Record the requirement in the tender clarification tracker."

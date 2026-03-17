"""Tender submission checklist generation."""

from __future__ import annotations

from .tender_models import ChecklistItem, TenderRequirement


def build_submission_checklist(requirements: list[TenderRequirement]) -> list[ChecklistItem]:
    """Convert extracted requirements into a practical review checklist."""

    checklist: list[ChecklistItem] = []
    for requirement in requirements:
        notes = requirement.notes
        if requirement.review_flag:
            notes = (notes + " Human review required.").strip()
        checklist.append(
            ChecklistItem(
                requirement_id=requirement.requirement_id,
                category=requirement.category,
                description=requirement.description,
                mandatory=requirement.mandatory,
                source_reference=requirement.source_reference,
                confidence=requirement.confidence,
                action_needed=requirement.action_needed,
                owner=requirement.owner,
                status=requirement.status,
                notes=notes,
            )
        )
    return checklist

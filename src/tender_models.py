"""Typed models for tender analysis workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class TenderSourceLine:
    """A normalized source line extracted from a tender input file."""

    source_reference: str
    text: str
    line_number: int
    sheet_name: str = ""


@dataclass(slots=True)
class TenderDocument:
    """Normalized tender document content used by the analysis workflow."""

    source_path: Path
    document_name: str
    document_type: str
    title: str
    text: str
    lines: list[TenderSourceLine] = field(default_factory=list)


@dataclass(slots=True)
class TenderRequirement:
    """Extracted tender requirement or instruction candidate."""

    requirement_id: str
    category: str
    description: str
    mandatory: bool
    source_reference: str
    confidence: float
    action_needed: str
    owner: str
    status: str = "pending review"
    notes: str = ""
    matched_phrase: str = ""
    extracted_text: str = ""
    review_flag: bool = False


@dataclass(slots=True)
class ChecklistItem:
    """Review-oriented tender submission checklist item."""

    requirement_id: str
    category: str
    description: str
    mandatory: bool
    source_reference: str
    confidence: float
    action_needed: str
    owner: str
    status: str = "pending"
    notes: str = ""


@dataclass(slots=True)
class ScopeSection:
    """Detected tender scope section with source references."""

    section_name: str
    confidence: float
    source_references: list[str] = field(default_factory=list)
    matched_keywords: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass(slots=True)
class DraftBOQSuggestion:
    """Review-first suggested BOQ line derived from tender text."""

    section: str
    description: str
    unit: str
    quantity_placeholder: str
    rate_placeholder: str
    amount_placeholder: str
    source_basis: str
    source_reference: str
    confidence: float
    source_excerpt: str = ""
    review_flag: bool = True
    notes: str = ""


@dataclass(slots=True)
class BOQGapItem:
    """Gap or inconsistency between tender scope and an available BOQ."""

    gap_type: str
    section: str
    description: str
    source_reference: str
    existing_boq_reference: str = ""
    confidence: float = 0.0
    review_flag: bool = True
    notes: str = ""


@dataclass(slots=True)
class ClarificationEntry:
    """Potential clarification item that should be reviewed by the QS team."""

    clarification_id: str
    category: str
    description: str
    source_reference: str
    confidence: float
    action_needed: str
    review_flag: bool = True
    notes: str = ""


@dataclass(slots=True)
class PricingHandoffRow:
    """Intermediate pricing handoff row for integrated tender-to-price workflows."""

    section: str
    description: str
    unit: str
    quantity: float | None
    source_basis: str
    source_origin: str
    inferred_from_tender: bool
    confidence: float
    review_required: bool = True
    notes: str = ""
    source_reference: str = ""


@dataclass(slots=True)
class TenderAnalysisSummary:
    """High-level tender analysis summary for quick review."""

    document_name: str
    title: str
    total_requirements: int
    mandatory_requirements: int
    flagged_requirements: int
    checklist_items: int
    scope_sections: int
    detected_scope: list[str] = field(default_factory=list)
    commercial_clues: list[str] = field(default_factory=list)
    review_notes: list[str] = field(default_factory=list)
    gap_items: int = 0
    draft_suggestions: int = 0
    clarifications: int = 0


@dataclass(slots=True)
class TenderAnalysisResult:
    """Full tender analysis output."""

    document: TenderDocument
    requirements: list[TenderRequirement] = field(default_factory=list)
    checklist_items: list[ChecklistItem] = field(default_factory=list)
    scope_sections: list[ScopeSection] = field(default_factory=list)
    draft_suggestions: list[DraftBOQSuggestion] = field(default_factory=list)
    gap_items: list[BOQGapItem] = field(default_factory=list)
    clarifications: list[ClarificationEntry] = field(default_factory=list)
    pricing_handoff: list[PricingHandoffRow] = field(default_factory=list)
    summary: TenderAnalysisSummary | None = None
    output_workbook: Path | None = None
    output_json: Path | None = None

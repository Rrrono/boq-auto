"""Typed models for BOQ AUTO."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class RateItem:
    item_code: str
    description: str
    normalized_description: str
    section: str
    subsection: str
    unit: str
    rate: float
    currency: str
    region: str
    source: str
    source_sheet: str
    source_page: str
    basis: str
    crew_type: str
    plant_type: str
    material_type: str
    keywords: str
    alias_group: str
    build_up_recipe_id: str
    confidence_hint: float
    notes: str
    active: bool = True


@dataclass(slots=True)
class AliasEntry:
    alias: str
    canonical_term: str
    section_bias: str
    notes: str = ""


@dataclass(slots=True)
class SectionRule:
    trigger_text: str
    inferred_section: str
    priority: int = 0


@dataclass(slots=True)
class BuildUpInput:
    input_code: str
    input_type: str
    description: str
    unit: str
    rate: float
    region: str
    source: str
    active: bool = True


@dataclass(slots=True)
class BuildUpRecipeLine:
    recipe_id: str
    recipe_name: str
    output_description: str
    output_unit: str
    section: str
    component_code: str
    factor: float
    waste_factor: float
    notes: str = ""


@dataclass(slots=True)
class RegionalAdjustment:
    region: str
    section: str
    factor: float
    notes: str = ""
    active: bool = True


@dataclass(slots=True)
class TextListEntry:
    text: str
    category: str = ""
    active: bool = True


@dataclass(slots=True)
class DatabaseBundle:
    rate_items: list[RateItem] = field(default_factory=list)
    aliases: list[AliasEntry] = field(default_factory=list)
    section_rules: list[SectionRule] = field(default_factory=list)
    build_inputs: list[BuildUpInput] = field(default_factory=list)
    build_recipes: list[BuildUpRecipeLine] = field(default_factory=list)
    regional_adjustments: list[RegionalAdjustment] = field(default_factory=list)
    assumptions: list[TextListEntry] = field(default_factory=list)
    exclusions: list[TextListEntry] = field(default_factory=list)
    controls: dict[str, str] = field(default_factory=dict)
    rules: list[dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class ColumnMap:
    header_row: int
    description_col: int | None = None
    unit_col: int | None = None
    quantity_col: int | None = None
    rate_col: int | None = None
    amount_col: int | None = None


@dataclass(slots=True)
class BOQLine:
    sheet_name: str
    row_number: int
    description: str
    unit: str = ""
    quantity: float | None = None
    rate: float | None = None
    amount: float | None = None
    inferred_section: str = ""
    normalized_description: str = ""
    is_heading: bool = False
    is_subtotal: bool = False
    is_total: bool = False
    is_summary_row: bool = False


@dataclass(slots=True)
class SheetData:
    sheet_name: str
    columns: ColumnMap
    classification: str = "boq"
    rows: list[BOQLine] = field(default_factory=list)


@dataclass(slots=True)
class MatchResult:
    boq_line: BOQLine
    decision: str
    matched_item_code: str = ""
    matched_description: str = ""
    matched_unit: str = ""
    base_rate: float | None = None
    rate: float | None = None
    confidence_score: float = 0.0
    review_flag: bool = False
    section_used: str = ""
    source: str = ""
    region_used: str = ""
    built_up: bool = False
    basis_of_rate: str = ""
    approval_status: str = "Pending Pricing Review"
    commercial_review_flags: list[str] = field(default_factory=list)
    alternate_options: list[str] = field(default_factory=list)
    regional_factor: float = 1.0
    rationale: list[str] = field(default_factory=list)


@dataclass(slots=True)
class CommercialTerms:
    overhead_pct: float = 0.0
    profit_pct: float = 0.0
    risk_pct: float = 0.0
    vat_pct: float = 0.0
    default_approval_status: str = "Pending Commercial Review"


@dataclass(slots=True)
class SectionSummary:
    section: str
    subtotal: float


@dataclass(slots=True)
class QuotationSummary:
    section_totals: list[SectionSummary] = field(default_factory=list)
    currency: str = "KES"
    subtotal: float = 0.0
    overhead_amount: float = 0.0
    profit_amount: float = 0.0
    risk_amount: float = 0.0
    pre_vat_total: float = 0.0
    vat_amount: float = 0.0
    grand_total: float = 0.0
    matched_items: int = 0
    flagged_items: int = 0
    bid_ready: bool = False
    bid_ready_reason: str = ""


@dataclass(slots=True)
class AppConfig:
    data: dict[str, Any]

    @property
    def log_level(self) -> str:
        return str(self.data.get("app", {}).get("log_level", "INFO"))

    @property
    def log_file(self) -> str:
        return str(self.data.get("app", {}).get("log_file", "logs/boq_auto.log"))

    @property
    def default_region(self) -> str:
        return str(self.data.get("app", {}).get("default_region", "Nairobi"))

    @property
    def default_currency(self) -> str:
        return str(self.data.get("app", {}).get("default_currency", "KES"))

    @property
    def boq_dir(self) -> str:
        return str(self.data.get("paths", {}).get("boq_dir", "boq"))

    @property
    def database_dir(self) -> str:
        return str(self.data.get("paths", {}).get("database_dir", "database"))

    @property
    def output_dir(self) -> str:
        return str(self.data.get("paths", {}).get("output_dir", "output"))

    def get(self, dotted_key: str, default: Any = None) -> Any:
        current: Any = self.data
        for part in dotted_key.split("."):
            if not isinstance(current, dict) or part not in current:
                return default
            current = current[part]
        return current


@dataclass(slots=True)
class RunArtifacts:
    output_workbook: Path
    unmatched_csv: Path | None
    audit_json: Path | None
    processed: int
    matched: int
    flagged: int
    quotation_summary: QuotationSummary | None = None

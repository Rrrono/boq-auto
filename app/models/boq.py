"""Pydantic models for the cloud BOQ API."""

from __future__ import annotations

from io import BytesIO

from pydantic import BaseModel, ConfigDict, Field


class ParsedBoqItem(BaseModel):
    description: str
    unit: str = ""
    quantity: float | None = None
    rate: float | None = None
    amount: float | None = None
    sheet_name: str
    row_number: int
    inferred_section: str = ""
    spec_attributes: str = ""
    decision: str = ""
    matched_item_code: str = ""
    matched_description: str = ""
    confidence_score: float = 0.0
    review_flag: bool = False
    basis_of_rate: str = ""


class CostSummary(BaseModel):
    currency: str = "KES"
    region: str
    item_count: int
    priced_item_count: int
    matched_count: int = 0
    flagged_count: int = 0
    total_cost: float
    average_rate: float = 0.0


class BoqProcessingResponse(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    filename: str
    output_filename: str
    region: str
    summary: CostSummary
    items: list[ParsedBoqItem] = Field(default_factory=list)
    database_path: str = ""
    input_storage_uri: str | None = None
    output_storage_uri: str | None = None
    audit_storage_uri: str | None = None
    workbook_bytes: bytes = Field(default=b"", exclude=True)

    def workbook_stream(self) -> BytesIO:
        return BytesIO(self.workbook_bytes)

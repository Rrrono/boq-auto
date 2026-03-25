"""In-memory workbook parsing for uploaded BOQs."""

from __future__ import annotations

import logging
from io import BytesIO

import pandas as pd

from app.models.boq import ParsedBoqItem
from src.config_loader import load_config
from src.excel_loader import load_workbook_safe
from src.section_inference import infer_section
from src.workbook_reader import WorkbookReader


LOGGER = logging.getLogger("boq_auto.api.file_parser")


class InvalidWorkbookError(ValueError):
    """Raised when an uploaded workbook cannot be parsed."""


def parse_boq_file(file_bytes: bytes, filename: str) -> list[ParsedBoqItem]:
    """Parse an uploaded BOQ workbook directly from bytes."""
    if not file_bytes:
        raise InvalidWorkbookError("Uploaded workbook is empty.")

    try:
        workbook = load_workbook_safe(BytesIO(file_bytes))
    except Exception as exc:  # pragma: no cover - workbook parser boundary
        raise InvalidWorkbookError(f"Could not read Excel workbook '{filename}'.") from exc

    config = load_config()
    reader = WorkbookReader(config=config, logger=LOGGER)
    sheets = reader.read_workbook(workbook)

    parsed_items: list[ParsedBoqItem] = []
    for sheet in sheets:
        nearby_headings: list[str] = []
        for row in sheet.rows:
            if row.is_heading:
                nearby_headings.append(row.description)
                continue
            if row.is_subtotal or row.is_total or row.is_summary_row:
                continue
            row.inferred_section = infer_section(sheet.sheet_name, row, nearby_headings, [])
            parsed_items.append(
                ParsedBoqItem(
                    description=row.description,
                    unit=row.unit,
                    quantity=row.quantity,
                    rate=row.rate,
                    amount=row.amount,
                    sheet_name=row.sheet_name,
                    row_number=row.row_number,
                    inferred_section=row.inferred_section,
                    spec_attributes=row.spec_attributes,
                )
            )

    if not parsed_items:
        raise InvalidWorkbookError(f"No BOQ-style line items were detected in '{filename}'.")

    frame = pd.DataFrame([item.model_dump() for item in parsed_items])
    LOGGER.info("parsed_boq | filename=%s | rows=%s | sheets=%s", filename, len(frame), frame["sheet_name"].nunique())
    return parsed_items

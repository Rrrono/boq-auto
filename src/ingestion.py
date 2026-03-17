"""Manual ingestion helpers for growing the Excel rate database."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from openpyxl import Workbook, load_workbook

from .normalizer import normalize_text, normalize_unit
from .utils import safe_float, truthy

RATE_LIBRARY_HEADERS = [
    "item_code", "description", "normalized_description", "section", "subsection", "unit", "rate",
    "currency", "region", "source", "source_sheet", "source_page", "basis", "crew_type", "plant_type",
    "material_type", "keywords", "alias_group", "build_up_recipe_id", "confidence_hint", "notes", "active",
]

BUILDUP_INPUT_HEADERS = [
    "input_code", "input_type", "description", "unit", "rate", "region", "source", "active",
]

CANDIDATE_MATCH_HEADERS = [
    "timestamp", "import_batch_id", "source_file", "source_sheet", "target_sheet", "item_code",
    "description", "normalized_description", "section", "subsection", "unit", "rate", "currency", "region",
    "source", "source_page", "basis", "crew_type", "plant_type", "material_type", "keywords", "alias_group",
    "build_up_recipe_id", "confidence_hint", "notes", "active", "duplicate_reason", "matched_item_code",
    "reviewer_status", "reviewer_name", "reviewed_at", "review_decision", "promote_target",
    "approved_item_code", "approved_description", "approved_rate", "approved_canonical_term",
    "approved_section_bias", "confidence_override", "reviewer_note", "promotion_status", "promoted_at",
]

REVIEW_LOG_HEADERS = [
    "timestamp", "boq_file", "sheet_name", "row_number", "boq_description", "decision",
    "matched_item_code", "matched_description", "confidence_score", "reviewer_note",
]

CANDIDATE_REVIEW_HEADERS = [
    "candidate_row_number", "reviewer_status", "reviewer_name", "reviewed_at", "review_decision",
    "promote_target", "approved_item_code", "approved_description", "approved_rate", "approved_canonical_term",
    "approved_section_bias", "confidence_override", "reviewer_note", "source_file", "target_sheet", "item_code",
    "matched_item_code", "description", "section", "subsection", "unit", "rate", "currency", "region",
    "basis", "duplicate_reason", "promotion_status",
]

ALIASES_HEADERS = ["alias", "canonical_term", "section_bias", "notes"]

SOURCE_FIELD_ALIASES = {
    "item_code": ["item_code", "code", "item", "rate_code"],
    "input_code": ["input_code", "code", "item_code", "resource_code"],
    "description": ["description", "item_description", "particulars", "resource_description", "name"],
    "section": ["section", "trade", "bill_section", "category"],
    "subsection": ["subsection", "sub_section", "subtrade"],
    "unit": ["unit", "uom", "measure"],
    "rate": ["rate", "price", "unit_rate", "cost"],
    "currency": ["currency"],
    "region": ["region", "county", "location", "market"],
    "source": ["source", "manual", "library", "origin"],
    "source_sheet": ["source_sheet", "sheet", "sheet_name"],
    "source_page": ["source_page", "page", "page_no"],
    "basis": ["basis", "basis_of_rate"],
    "crew_type": ["crew_type", "labour_type"],
    "plant_type": ["plant_type", "equipment_type"],
    "material_type": ["material_type", "material_group"],
    "keywords": ["keywords", "tags"],
    "alias_group": ["alias_group"],
    "build_up_recipe_id": ["build_up_recipe_id", "recipe_id"],
    "confidence_hint": ["confidence_hint", "confidence"],
    "notes": ["notes", "remark", "remarks"],
    "active": ["active", "status"],
    "input_type": ["input_type", "resource_type", "type"],
}

REGION_ALIASES = {
    "nrb": "Nairobi",
    "nai": "Nairobi",
    "nairobi county": "Nairobi",
    "nyanza region": "Nyanza",
    "kisumu": "Nyanza",
    "western kenya": "Western",
}


@dataclass(slots=True)
class ImportSummary:
    target_sheet: str
    source_file: str
    total_rows: int = 0
    appended: int = 0
    skipped_duplicates: int = 0
    candidates_created: int = 0
    merged: int = 0
    normalized_rows: int = 0
    reviewed: int = 0
    rejected: int = 0
    promoted: int = 0
    report_rows: int = 0
    training_records: int = 0
    notes: list[str] = field(default_factory=list)


def normalize_region_name(region: str) -> str:
    """Normalize common region and county labels into a consistent market name."""
    text = normalize_text(region)
    if not text:
        return ""
    return REGION_ALIASES.get(text, text.title())


def timestamp_now() -> str:
    """Return a stable import timestamp."""
    return datetime.now().isoformat(timespec="seconds")


def ensure_sheet_headers(workbook: Workbook, sheet_name: str, headers: list[str]):
    """Create an optional sheet if it does not yet exist and validate its header row."""
    if sheet_name not in workbook.sheetnames:
        sheet = workbook.create_sheet(sheet_name)
        sheet.append(headers)
        return sheet
    sheet = workbook[sheet_name]
    existing_headers = [str(cell.value or "").strip() for cell in next(sheet.iter_rows(min_row=1, max_row=1))]
    if not existing_headers or all(not header for header in existing_headers):
        sheet.delete_rows(1, 1)
        sheet.append(headers)
        return sheet
    missing = [header for header in headers if header not in existing_headers]
    if missing:
        for header in missing:
            sheet.cell(1, sheet.max_column + 1).value = header
    return sheet


def workbook_headers(sheet) -> list[str]:
    """Return normalized headers for a worksheet."""
    return [str(cell.value or "").strip() for cell in next(sheet.iter_rows(min_row=1, max_row=1))]


def read_structured_table(input_path: str, sheet_name: str | None = None) -> list[dict[str, Any]]:
    """Read a CSV or Excel table into a list of row dictionaries."""
    path = Path(input_path)
    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))

    workbook = load_workbook(path, data_only=True)
    worksheet = workbook[sheet_name] if sheet_name and sheet_name in workbook.sheetnames else workbook[workbook.sheetnames[0]]
    headers = workbook_headers(worksheet)
    rows: list[dict[str, Any]] = []
    for row in worksheet.iter_rows(min_row=2, values_only=True):
        rows.append(dict(zip(headers, row)))
    return rows


def lookup_value(row: dict[str, Any], field: str, default: Any = "") -> Any:
    """Find a source field using the known alias list."""
    normalized = {normalize_text(str(key)): value for key, value in row.items()}
    for alias in SOURCE_FIELD_ALIASES.get(field, [field]):
        key = normalize_text(alias)
        if key in normalized and normalized[key] not in (None, ""):
            return normalized[key]
    return default


def append_row(sheet, headers: list[str], values: dict[str, Any]) -> None:
    """Append a row to a sheet using header order."""
    sheet_headers = workbook_headers(sheet)
    sheet.append([values.get(header, "") for header in sheet_headers or headers])


def build_rate_library_row(
    row: dict[str, Any],
    source_file: str,
    source_sheet: str,
    defaults: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Map a source row into the RateLibrary structure."""
    defaults = defaults or {}
    description = str(lookup_value(row, "description", defaults.get("description", ""))).strip()
    unit = normalize_unit(str(lookup_value(row, "unit", defaults.get("unit", ""))))
    region = normalize_region_name(str(lookup_value(row, "region", defaults.get("region", ""))))
    return {
        "item_code": str(lookup_value(row, "item_code", defaults.get("item_code", ""))).strip(),
        "description": description,
        "normalized_description": normalize_text(description),
        "section": str(lookup_value(row, "section", defaults.get("section", ""))).strip(),
        "subsection": str(lookup_value(row, "subsection", defaults.get("subsection", ""))).strip(),
        "unit": unit,
        "rate": safe_float(lookup_value(row, "rate", defaults.get("rate", 0.0))) or 0.0,
        "currency": str(lookup_value(row, "currency", defaults.get("currency", "KES"))).strip() or "KES",
        "region": region,
        "source": str(lookup_value(row, "source", defaults.get("source", source_file))).strip() or source_file,
        "source_sheet": str(lookup_value(row, "source_sheet", defaults.get("source_sheet", source_sheet))).strip() or source_sheet,
        "source_page": str(lookup_value(row, "source_page", defaults.get("source_page", ""))).strip(),
        "basis": str(lookup_value(row, "basis", defaults.get("basis", "Imported source table"))).strip(),
        "crew_type": str(lookup_value(row, "crew_type", defaults.get("crew_type", ""))).strip(),
        "plant_type": str(lookup_value(row, "plant_type", defaults.get("plant_type", ""))).strip(),
        "material_type": str(lookup_value(row, "material_type", defaults.get("material_type", ""))).strip(),
        "keywords": str(lookup_value(row, "keywords", defaults.get("keywords", ""))).strip(),
        "alias_group": str(lookup_value(row, "alias_group", defaults.get("alias_group", ""))).strip(),
        "build_up_recipe_id": str(lookup_value(row, "build_up_recipe_id", defaults.get("build_up_recipe_id", ""))).strip(),
        "confidence_hint": safe_float(lookup_value(row, "confidence_hint", defaults.get("confidence_hint", 0.0))) or 0.0,
        "notes": str(lookup_value(row, "notes", defaults.get("notes", ""))).strip(),
        "active": defaults.get("active", True if lookup_value(row, "active", True) in (None, "") else truthy(lookup_value(row, "active", True))),
    }


def build_buildup_input_row(
    row: dict[str, Any],
    source_file: str,
    source_sheet: str = "",
    defaults: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Map a source row into the BuildUpInputs structure."""
    defaults = defaults or {}
    description = str(lookup_value(row, "description", defaults.get("description", ""))).strip()
    return {
        "input_code": str(lookup_value(row, "input_code", defaults.get("input_code", ""))).strip(),
        "input_type": str(lookup_value(row, "input_type", defaults.get("input_type", ""))).strip(),
        "description": description,
        "unit": normalize_unit(str(lookup_value(row, "unit", defaults.get("unit", "")))),
        "rate": safe_float(lookup_value(row, "rate", defaults.get("rate", 0.0))) or 0.0,
        "region": normalize_region_name(str(lookup_value(row, "region", defaults.get("region", "")))),
        "source": str(lookup_value(row, "source", defaults.get("source", source_file))).strip() or source_file,
        "active": defaults.get("active", True if lookup_value(row, "active", True) in (None, "") else truthy(lookup_value(row, "active", True))),
    }


def existing_rate_indexes(sheet) -> tuple[dict[str, int], dict[tuple[str, str], int]]:
    """Build duplicate-detection indexes for RateLibrary or BuildUpInputs sheets."""
    headers = workbook_headers(sheet)
    code_field = "item_code" if "item_code" in headers else "input_code"
    description_field = "normalized_description" if "normalized_description" in headers else "description"
    code_index: dict[str, int] = {}
    desc_unit_index: dict[tuple[str, str], int] = {}
    header_pos = {header: idx for idx, header in enumerate(headers)}
    for row_number, values in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
        item_code = str(values[header_pos[code_field]] or "").strip()
        description = str(values[header_pos[description_field]] or "").strip()
        if description_field == "description":
            description = normalize_text(description)
        unit = normalize_unit(str(values[header_pos["unit"]] or ""))
        if item_code:
            code_index[item_code] = row_number
        if description and unit:
            desc_unit_index[(description, unit)] = row_number
    return code_index, desc_unit_index


def write_candidate_match(
    workbook: Workbook,
    candidate_row: dict[str, Any],
) -> None:
    """Append an uncertain import to CandidateMatches."""
    sheet = ensure_sheet_headers(workbook, "CandidateMatches", CANDIDATE_MATCH_HEADERS)
    append_row(sheet, CANDIDATE_MATCH_HEADERS, candidate_row)


def write_review_log(workbook: Workbook, note: dict[str, Any]) -> None:
    """Append an automated review or merge action to ReviewLog."""
    sheet = ensure_sheet_headers(workbook, "ReviewLog", REVIEW_LOG_HEADERS)
    append_row(sheet, REVIEW_LOG_HEADERS, note)


def candidate_positions(sheet) -> dict[str, int]:
    """Return header positions for CandidateMatches-like sheets."""
    return {header: index + 1 for index, header in enumerate(workbook_headers(sheet))}


def set_candidate_defaults(sheet) -> None:
    """Ensure review workflow defaults exist on candidate rows."""
    positions = candidate_positions(sheet)
    for row_number in range(2, sheet.max_row + 1):
        if "reviewer_status" in positions and not sheet.cell(row_number, positions["reviewer_status"]).value:
            sheet.cell(row_number, positions["reviewer_status"]).value = "pending"
        if "review_decision" in positions and not sheet.cell(row_number, positions["review_decision"]).value:
            sheet.cell(row_number, positions["review_decision"]).value = "hold"
        if "promote_target" in positions and not sheet.cell(row_number, positions["promote_target"]).value:
            sheet.cell(row_number, positions["promote_target"]).value = "candidatematches"
        if "promotion_status" in positions and not sheet.cell(row_number, positions["promotion_status"]).value:
            sheet.cell(row_number, positions["promotion_status"]).value = "not_promoted"


def import_structured_rows(
    db_path: str,
    input_path: str,
    target_sheet: str,
    mapper,
    defaults: dict[str, Any] | None = None,
    source_sheet: str | None = None,
) -> ImportSummary:
    """Import structured rows into a target database sheet with duplicate handling."""
    workbook = load_workbook(db_path)
    target_headers = RATE_LIBRARY_HEADERS if target_sheet == "RateLibrary" else BUILDUP_INPUT_HEADERS
    target = ensure_sheet_headers(workbook, target_sheet, target_headers)
    candidate_sheet = ensure_sheet_headers(workbook, "CandidateMatches", CANDIDATE_MATCH_HEADERS)
    set_candidate_defaults(candidate_sheet)
    ensure_sheet_headers(workbook, "ReviewLog", REVIEW_LOG_HEADERS)
    rows = read_structured_table(input_path, source_sheet)
    code_index, desc_unit_index = existing_rate_indexes(target)

    batch_id = f"import-{timestamp_now().replace(':', '').replace('-', '')}"
    summary = ImportSummary(target_sheet=target_sheet, source_file=input_path, total_rows=len(rows))

    for raw_row in rows:
        mapped = mapper(raw_row, Path(input_path).name, source_sheet or "")
        if defaults:
            mapped = {**mapped, **{key: value for key, value in defaults.items() if value not in (None, "")}}
        if not mapped.get("description"):
            summary.notes.append("Skipped row with blank description.")
            continue

        item_code_key = "item_code" if target_sheet == "RateLibrary" else "input_code"
        item_code = str(mapped.get(item_code_key, "")).strip()
        normalized_description = str(mapped.get("normalized_description") or normalize_text(mapped.get("description", ""))).strip()
        unit = normalize_unit(str(mapped.get("unit", "")))
        duplicate_reason = ""
        matched_item_code = ""

        if item_code and item_code in code_index:
            duplicate_reason = f"duplicate {item_code_key}"
            matched_item_code = item_code
        elif normalized_description and unit and (normalized_description, unit) in desc_unit_index:
            duplicate_reason = "duplicate normalized description + unit"
            matched_item_code = str(mapped.get(item_code_key, "")) or str(desc_unit_index[(normalized_description, unit)])

        if duplicate_reason:
            existing_row_number = code_index.get(item_code) or desc_unit_index.get((normalized_description, unit))
            existing_rate = safe_float(target.cell(existing_row_number, workbook_headers(target).index("rate") + 1).value) if existing_row_number else None
            incoming_rate = safe_float(mapped.get("rate"))
            materially_different = existing_rate is None or incoming_rate is None or abs(existing_rate - incoming_rate) > 0.001
            if materially_different:
                write_candidate_match(
                    workbook,
                    {
                        "timestamp": timestamp_now(),
                        "import_batch_id": batch_id,
                        "source_file": Path(input_path).name,
                        "source_sheet": source_sheet or "",
                        "target_sheet": target_sheet,
                        "item_code": mapped.get("item_code") or mapped.get("input_code", ""),
                        "description": mapped.get("description", ""),
                        "normalized_description": normalized_description,
                        "section": mapped.get("section", ""),
                        "subsection": mapped.get("subsection", ""),
                        "unit": unit,
                        "rate": mapped.get("rate", ""),
                        "currency": mapped.get("currency", ""),
                        "region": mapped.get("region", ""),
                        "source": mapped.get("source", ""),
                        "source_page": mapped.get("source_page", ""),
                        "basis": mapped.get("basis", ""),
                        "crew_type": mapped.get("crew_type", ""),
                        "plant_type": mapped.get("plant_type", ""),
                        "material_type": mapped.get("material_type", ""),
                        "keywords": mapped.get("keywords", ""),
                        "alias_group": mapped.get("alias_group", ""),
                        "build_up_recipe_id": mapped.get("build_up_recipe_id", ""),
                        "confidence_hint": mapped.get("confidence_hint", 0.0),
                        "notes": mapped.get("notes", ""),
                        "active": mapped.get("active", True),
                        "duplicate_reason": duplicate_reason,
                        "matched_item_code": matched_item_code,
                        "reviewer_status": "pending",
                        "reviewer_name": "",
                        "reviewed_at": "",
                        "review_decision": "hold",
                        "promote_target": "candidatematches",
                        "approved_item_code": "",
                        "approved_description": "",
                        "approved_rate": "",
                        "approved_canonical_term": "",
                        "approved_section_bias": "",
                        "confidence_override": "",
                        "reviewer_note": "",
                        "promotion_status": "not_promoted",
                        "promoted_at": "",
                    },
                )
                summary.candidates_created += 1
            else:
                summary.skipped_duplicates += 1
            continue

        append_row(target, target_headers, mapped)
        if item_code:
            code_index[item_code] = target.max_row
        desc_unit_index[(normalized_description, unit)] = target.max_row
        summary.appended += 1

    workbook.save(db_path)
    return summary


def normalize_database_units(db_path: str, sheets: list[str] | None = None) -> ImportSummary:
    """Normalize units, regions, and descriptions across database sheets."""
    workbook = load_workbook(db_path)
    target_sheets = sheets or ["RateLibrary", "BuildUpInputs", "CandidateMatches"]
    summary = ImportSummary(target_sheet="multiple", source_file=db_path)
    for sheet_name in target_sheets:
        if sheet_name not in workbook.sheetnames:
            continue
        sheet = workbook[sheet_name]
        headers = workbook_headers(sheet)
        positions = {header: index + 1 for index, header in enumerate(headers)}
        for row_number in range(2, sheet.max_row + 1):
            if "unit" in positions:
                cell = sheet.cell(row_number, positions["unit"])
                normalized = normalize_unit(str(cell.value or ""))
                if normalized and normalized != str(cell.value or ""):
                    cell.value = normalized
                    summary.normalized_rows += 1
            if "region" in positions:
                cell = sheet.cell(row_number, positions["region"])
                normalized_region = normalize_region_name(str(cell.value or ""))
                if normalized_region and normalized_region != str(cell.value or ""):
                    cell.value = normalized_region
                    summary.normalized_rows += 1
            if "description" in positions and "normalized_description" in positions:
                description = str(sheet.cell(row_number, positions["description"]).value or "")
                sheet.cell(row_number, positions["normalized_description"]).value = normalize_text(description)
    workbook.save(db_path)
    return summary


def deduplicate_database(db_path: str, sheet_name: str = "RateLibrary") -> ImportSummary:
    """Deactivate duplicate rows based on item code and normalized description plus unit."""
    workbook = load_workbook(db_path)
    sheet = ensure_sheet_headers(workbook, sheet_name, RATE_LIBRARY_HEADERS if sheet_name == "RateLibrary" else BUILDUP_INPUT_HEADERS)
    ensure_sheet_headers(workbook, "ReviewLog", REVIEW_LOG_HEADERS)
    headers = workbook_headers(sheet)
    positions = {header: index + 1 for index, header in enumerate(headers)}
    seen_codes: set[str] = set()
    seen_desc_units: set[tuple[str, str]] = set()
    summary = ImportSummary(target_sheet=sheet_name, source_file=db_path)

    for row_number in range(2, sheet.max_row + 1):
        code_field = "item_code" if "item_code" in positions else "input_code"
        item_code = str(sheet.cell(row_number, positions[code_field]).value or "").strip()
        normalized_description = str(sheet.cell(row_number, positions.get("normalized_description", positions["description"])).value or "").strip()
        if "normalized_description" not in positions:
            normalized_description = normalize_text(normalized_description)
        unit = normalize_unit(str(sheet.cell(row_number, positions["unit"]).value or ""))
        duplicate = False
        if item_code and item_code in seen_codes:
            duplicate = True
        elif normalized_description and unit and (normalized_description, unit) in seen_desc_units:
            duplicate = True

        if duplicate and "active" in positions:
            sheet.cell(row_number, positions["active"]).value = False
            summary.skipped_duplicates += 1
            write_review_log(
                workbook,
                {
                    "timestamp": timestamp_now(),
                    "boq_file": db_path,
                    "sheet_name": sheet_name,
                    "row_number": row_number,
                    "boq_description": normalized_description,
                    "decision": "duplicate-deactivated",
                    "matched_item_code": item_code,
                    "matched_description": normalized_description,
                    "confidence_score": 100,
                    "reviewer_note": "Automated deduplication pass",
                },
            )
            continue

        if item_code:
            seen_codes.add(item_code)
        if normalized_description and unit:
            seen_desc_units.add((normalized_description, unit))

    workbook.save(db_path)
    return summary


def generate_review_report(db_path: str, output_json: str | None = None) -> ImportSummary:
    """Generate or refresh a Candidate Review sheet and optional training-style JSON."""
    workbook = load_workbook(db_path)
    candidate_sheet = ensure_sheet_headers(workbook, "CandidateMatches", CANDIDATE_MATCH_HEADERS)
    set_candidate_defaults(candidate_sheet)
    if "Candidate Review" in workbook.sheetnames:
        del workbook["Candidate Review"]
    review_sheet = workbook.create_sheet("Candidate Review")
    review_sheet.append(CANDIDATE_REVIEW_HEADERS)

    cpos = candidate_positions(candidate_sheet)
    summary = ImportSummary(target_sheet="Candidate Review", source_file=db_path)
    training_rows: list[dict[str, Any]] = []

    for row_number in range(2, candidate_sheet.max_row + 1):
        row_data = {header: candidate_sheet.cell(row_number, cpos[header]).value for header in cpos}
        review_sheet.append(
            [
                row_number,
                row_data.get("reviewer_status", "pending"),
                row_data.get("reviewer_name", ""),
                row_data.get("reviewed_at", ""),
                row_data.get("review_decision", "hold"),
                row_data.get("promote_target", "candidatematches"),
                row_data.get("approved_item_code", ""),
                row_data.get("approved_description", ""),
                row_data.get("approved_rate", ""),
                row_data.get("approved_canonical_term", ""),
                row_data.get("approved_section_bias", ""),
                row_data.get("confidence_override", ""),
                row_data.get("reviewer_note", ""),
                row_data.get("source_file", ""),
                row_data.get("target_sheet", ""),
                row_data.get("item_code", ""),
                row_data.get("matched_item_code", ""),
                row_data.get("description", ""),
                row_data.get("section", ""),
                row_data.get("subsection", ""),
                row_data.get("unit", ""),
                row_data.get("rate", ""),
                row_data.get("currency", ""),
                row_data.get("region", ""),
                row_data.get("basis", ""),
                row_data.get("duplicate_reason", ""),
                row_data.get("promotion_status", "not_promoted"),
            ]
        )
        summary.report_rows += 1
        status = str(row_data.get("reviewer_status") or "").lower()
        if status in {"approved", "merge", "approved_for_merge"}:
            summary.reviewed += 1
        if status in {"rejected", "reject"}:
            summary.rejected += 1
        if status and status != "pending":
            training_rows.append(
                {
                    "candidate_row_number": row_number,
                    "reviewer_status": row_data.get("reviewer_status", ""),
                    "reviewer_name": row_data.get("reviewer_name", ""),
                    "reviewed_at": row_data.get("reviewed_at", ""),
                    "review_decision": row_data.get("review_decision", ""),
                    "promote_target": row_data.get("promote_target", ""),
                    "description": row_data.get("description", ""),
                    "normalized_description": row_data.get("normalized_description", ""),
                    "unit": row_data.get("unit", ""),
                    "rate": row_data.get("rate", ""),
                    "region": row_data.get("region", ""),
                    "matched_item_code": row_data.get("matched_item_code", ""),
                    "approved_item_code": row_data.get("approved_item_code", ""),
                    "approved_description": row_data.get("approved_description", ""),
                    "approved_canonical_term": row_data.get("approved_canonical_term", ""),
                    "confidence_hint": row_data.get("confidence_hint", ""),
                    "confidence_override": row_data.get("confidence_override", ""),
                    "reviewer_note": row_data.get("reviewer_note", ""),
                }
            )

    workbook.save(db_path)
    if output_json:
        Path(output_json).parent.mkdir(parents=True, exist_ok=True)
        Path(output_json).write_text(json.dumps(training_rows, indent=2, ensure_ascii=True), encoding="utf-8")
        summary.training_records = len(training_rows)
    return summary


def merge_reviewed_candidates(db_path: str, reviewer_name: str | None = None) -> ImportSummary:
    """Merge decisions from Candidate Review back into CandidateMatches and ReviewLog."""
    workbook = load_workbook(db_path)
    candidate_sheet = ensure_sheet_headers(workbook, "CandidateMatches", CANDIDATE_MATCH_HEADERS)
    set_candidate_defaults(candidate_sheet)
    if "Candidate Review" not in workbook.sheetnames:
        raise ValueError("Candidate Review sheet does not exist. Run review-report first.")
    review_sheet = workbook["Candidate Review"]
    ensure_sheet_headers(workbook, "ReviewLog", REVIEW_LOG_HEADERS)

    cpos = candidate_positions(candidate_sheet)
    rpos = {header: index + 1 for index, header in enumerate(workbook_headers(review_sheet))}
    summary = ImportSummary(target_sheet="CandidateMatches", source_file=db_path)

    for row_number in range(2, review_sheet.max_row + 1):
        candidate_row_number = int(safe_float(review_sheet.cell(row_number, rpos["candidate_row_number"]).value) or 0)
        if candidate_row_number < 2 or candidate_row_number > candidate_sheet.max_row:
            continue
        reviewer_status = str(review_sheet.cell(row_number, rpos["reviewer_status"]).value or "pending").strip()
        if not reviewer_status or reviewer_status.lower() == "pending":
            continue

        reviewed_at = str(review_sheet.cell(row_number, rpos["reviewed_at"]).value or "").strip() or timestamp_now()
        reviewer = str(review_sheet.cell(row_number, rpos["reviewer_name"]).value or reviewer_name or "").strip()
        review_decision = str(review_sheet.cell(row_number, rpos["review_decision"]).value or "hold").strip()
        promote_target = str(review_sheet.cell(row_number, rpos["promote_target"]).value or "candidatematches").strip().lower()
        approved_item_code = str(review_sheet.cell(row_number, rpos["approved_item_code"]).value or "").strip()
        approved_description = str(review_sheet.cell(row_number, rpos["approved_description"]).value or "").strip()
        approved_rate = review_sheet.cell(row_number, rpos["approved_rate"]).value
        approved_canonical_term = str(review_sheet.cell(row_number, rpos["approved_canonical_term"]).value or "").strip()
        approved_section_bias = str(review_sheet.cell(row_number, rpos["approved_section_bias"]).value or "").strip()
        confidence_override = review_sheet.cell(row_number, rpos["confidence_override"]).value
        reviewer_note = str(review_sheet.cell(row_number, rpos["reviewer_note"]).value or "").strip()

        updates = {
            "reviewer_status": reviewer_status.lower(),
            "reviewer_name": reviewer,
            "reviewed_at": reviewed_at,
            "review_decision": review_decision.lower(),
            "promote_target": promote_target,
            "approved_item_code": approved_item_code,
            "approved_description": approved_description,
            "approved_rate": approved_rate,
            "approved_canonical_term": approved_canonical_term,
            "approved_section_bias": approved_section_bias,
            "confidence_override": confidence_override,
            "reviewer_note": reviewer_note,
        }
        for field, value in updates.items():
            if field in cpos:
                candidate_sheet.cell(candidate_row_number, cpos[field]).value = value

        decision_label = "review-approved" if reviewer_status.lower() in {"approved", "merge", "approved_for_merge"} else "review-rejected"
        if reviewer_status.lower() in {"rejected", "reject"}:
            summary.rejected += 1
        else:
            summary.reviewed += 1
        write_review_log(
            workbook,
            {
                "timestamp": reviewed_at,
                "boq_file": db_path,
                "sheet_name": "CandidateMatches",
                "row_number": candidate_row_number,
                "boq_description": str(candidate_sheet.cell(candidate_row_number, cpos["description"]).value or ""),
                "decision": decision_label,
                "matched_item_code": str(candidate_sheet.cell(candidate_row_number, cpos["matched_item_code"]).value or ""),
                "matched_description": approved_description or str(candidate_sheet.cell(candidate_row_number, cpos["description"]).value or ""),
                "confidence_score": safe_float(confidence_override) or safe_float(candidate_sheet.cell(candidate_row_number, cpos["confidence_hint"]).value) or 0.0,
                "reviewer_note": reviewer_note or review_decision,
            },
        )

    workbook.save(db_path)
    return summary


def _promote_to_aliases(workbook: Workbook, row: dict[str, Any]) -> bool:
    """Promote an approved review row into Aliases."""
    sheet = ensure_sheet_headers(workbook, "Aliases", ALIASES_HEADERS)
    alias = str(row.get("description") or "").strip()
    canonical_term = str(row.get("approved_canonical_term") or row.get("approved_description") or row.get("description") or "").strip()
    if not alias or not canonical_term:
        return False
    existing = {(str(values[0] or "").strip().lower(), str(values[1] or "").strip().lower()) for values in sheet.iter_rows(min_row=2, values_only=True)}
    key = (alias.lower(), canonical_term.lower())
    if key in existing:
        return False
    sheet.append([alias, canonical_term, str(row.get("approved_section_bias") or row.get("section") or ""), str(row.get("reviewer_note") or "Promoted from review")])
    return True


def _promote_to_rate_library(workbook: Workbook, row: dict[str, Any]) -> bool:
    """Promote an approved review row into RateLibrary."""
    sheet = ensure_sheet_headers(workbook, "RateLibrary", RATE_LIBRARY_HEADERS)
    description = str(row.get("approved_description") or row.get("description") or "").strip()
    if not description:
        return False
    item_code = str(row.get("approved_item_code") or row.get("item_code") or "").strip()
    normalized_description = normalize_text(description)
    unit = normalize_unit(str(row.get("unit") or ""))
    existing_keys = {
        (
            str(values[0] or "").strip(),
            normalize_text(str(values[2] or values[1] or "")),
            normalize_unit(str(values[5] or "")),
        )
        for values in sheet.iter_rows(min_row=2, values_only=True)
    }
    key = (item_code, normalized_description, unit)
    if key in existing_keys:
        return False
    sheet.append(
        [
            item_code,
            description,
            normalized_description,
            str(row.get("section") or ""),
            str(row.get("subsection") or ""),
            unit,
            safe_float(row.get("approved_rate")) or safe_float(row.get("rate")) or 0.0,
            str(row.get("currency") or "KES"),
            normalize_region_name(str(row.get("region") or "")),
            str(row.get("source") or "Reviewed Match"),
            str(row.get("source_sheet") or "Candidate Review"),
            str(row.get("source_page") or ""),
            str(row.get("basis") or "Estimator-reviewed promotion"),
            str(row.get("crew_type") or ""),
            str(row.get("plant_type") or ""),
            str(row.get("material_type") or ""),
            str(row.get("keywords") or ""),
            str(row.get("alias_group") or ""),
            str(row.get("build_up_recipe_id") or ""),
            safe_float(row.get("confidence_override")) or safe_float(row.get("confidence_hint")) or 0.0,
            str(row.get("reviewer_note") or ""),
            True,
        ]
    )
    return True


def _retain_in_candidates(sheet, row_number: int) -> bool:
    """Mark an approved record as intentionally retained in CandidateMatches."""
    positions = candidate_positions(sheet)
    if "promotion_status" in positions:
        sheet.cell(row_number, positions["promotion_status"]).value = "retained_in_candidates"
    if "promoted_at" in positions:
        sheet.cell(row_number, positions["promoted_at"]).value = timestamp_now()
    return True


def promote_approved_candidates(db_path: str, output_json: str | None = None) -> ImportSummary:
    """Promote approved reviewed records into the selected live destination and export learning JSON."""
    workbook = load_workbook(db_path)
    candidate_sheet = ensure_sheet_headers(workbook, "CandidateMatches", CANDIDATE_MATCH_HEADERS)
    set_candidate_defaults(candidate_sheet)
    ensure_sheet_headers(workbook, "ReviewLog", REVIEW_LOG_HEADERS)
    summary = ImportSummary(target_sheet="CandidateMatches", source_file=db_path)
    cpos = candidate_positions(candidate_sheet)
    training_rows: list[dict[str, Any]] = []

    for row_number in range(2, candidate_sheet.max_row + 1):
        status = str(candidate_sheet.cell(row_number, cpos["reviewer_status"]).value or "").strip().lower()
        if status not in {"approved", "merge", "approved_for_merge"}:
            continue
        promotion_status = str(candidate_sheet.cell(row_number, cpos["promotion_status"]).value or "").strip().lower()
        if promotion_status in {"promoted", "retained_in_candidates"}:
            continue

        row = {header: candidate_sheet.cell(row_number, cpos[header]).value for header in cpos}
        target = str(row.get("promote_target") or "candidatematches").strip().lower()
        promoted = False
        if target == "aliases":
            promoted = _promote_to_aliases(workbook, row)
        elif target == "ratelibrary":
            promoted = _promote_to_rate_library(workbook, row)
        else:
            promoted = _retain_in_candidates(candidate_sheet, row_number)

        promoted_at = timestamp_now()
        if target == "candidatematches":
            promotion_status = "retained_in_candidates"
        else:
            promotion_status = "promoted" if promoted else "already_exists"
        candidate_sheet.cell(row_number, cpos["promotion_status"]).value = promotion_status
        candidate_sheet.cell(row_number, cpos["promoted_at"]).value = promoted_at
        summary.promoted += 1 if promoted else 0
        if not promoted and target != "candidatematches":
            summary.notes.append(f"Skipped duplicate promotion for candidate row {row_number} to {target}.")
        write_review_log(
            workbook,
            {
                "timestamp": promoted_at,
                "boq_file": db_path,
                "sheet_name": target if target != "candidatematches" else "CandidateMatches",
                "row_number": row_number,
                "boq_description": str(row.get("description") or ""),
                "decision": f"promoted-to-{target}",
                "matched_item_code": str(row.get("approved_item_code") or row.get("matched_item_code") or ""),
                "matched_description": str(row.get("approved_description") or row.get("description") or ""),
                "confidence_score": safe_float(row.get("confidence_override")) or safe_float(row.get("confidence_hint")) or 0.0,
                "reviewer_note": str(row.get("reviewer_note") or "Promoted approved review"),
            },
        )
        training_rows.append(
            {
                "timestamp": promoted_at,
                "candidate_row_number": row_number,
                "reviewer_status": row.get("reviewer_status", ""),
                "reviewer_name": row.get("reviewer_name", ""),
                "review_decision": row.get("review_decision", ""),
                "promote_target": target,
                "promotion_status": candidate_sheet.cell(row_number, cpos["promotion_status"]).value,
                "description": row.get("description", ""),
                "normalized_description": row.get("normalized_description", ""),
                "unit": row.get("unit", ""),
                "rate": row.get("rate", ""),
                "approved_rate": row.get("approved_rate", ""),
                "matched_item_code": row.get("matched_item_code", ""),
                "approved_item_code": row.get("approved_item_code", ""),
                "approved_description": row.get("approved_description", ""),
                "approved_canonical_term": row.get("approved_canonical_term", ""),
                "confidence_hint": row.get("confidence_hint", ""),
                "confidence_override": row.get("confidence_override", ""),
                "reviewer_note": row.get("reviewer_note", ""),
            }
        )

    workbook.save(db_path)
    if output_json:
        Path(output_json).parent.mkdir(parents=True, exist_ok=True)
        Path(output_json).write_text(json.dumps(training_rows, indent=2, ensure_ascii=True), encoding="utf-8")
        summary.training_records = len(training_rows)
    return summary


def merge_candidate_matches(db_path: str) -> ImportSummary:
    """Merge approved CandidateMatches entries into their target sheets and log the action."""
    workbook = load_workbook(db_path)
    candidate_sheet = ensure_sheet_headers(workbook, "CandidateMatches", CANDIDATE_MATCH_HEADERS)
    ensure_sheet_headers(workbook, "ReviewLog", REVIEW_LOG_HEADERS)
    summary = ImportSummary(target_sheet="CandidateMatches", source_file=db_path)
    headers = workbook_headers(candidate_sheet)
    positions = {header: index + 1 for index, header in enumerate(headers)}

    for row_number in range(2, candidate_sheet.max_row + 1):
        status = str(candidate_sheet.cell(row_number, positions["reviewer_status"]).value or "").strip().lower()
        if status not in {"approved", "approve_append", "approve_update"}:
            continue

        target_sheet_name = str(candidate_sheet.cell(row_number, positions["target_sheet"]).value or "RateLibrary")
        target_headers = RATE_LIBRARY_HEADERS if target_sheet_name == "RateLibrary" else BUILDUP_INPUT_HEADERS
        target_sheet = ensure_sheet_headers(workbook, target_sheet_name, target_headers)
        values = {header: candidate_sheet.cell(row_number, positions[header]).value for header in headers if header in positions}

        if target_sheet_name == "RateLibrary":
            row_values = {
                "item_code": values.get("item_code", ""),
                "description": values.get("description", ""),
                "normalized_description": values.get("normalized_description", ""),
                "section": values.get("section", ""),
                "subsection": values.get("subsection", ""),
                "unit": values.get("unit", ""),
                "rate": values.get("rate", ""),
                "currency": values.get("currency", "KES"),
                "region": values.get("region", ""),
                "source": values.get("source", ""),
                "source_sheet": values.get("source_sheet", ""),
                "source_page": values.get("source_page", ""),
                "basis": values.get("basis", ""),
                "crew_type": values.get("crew_type", ""),
                "plant_type": values.get("plant_type", ""),
                "material_type": values.get("material_type", ""),
                "keywords": values.get("keywords", ""),
                "alias_group": values.get("alias_group", ""),
                "build_up_recipe_id": values.get("build_up_recipe_id", ""),
                "confidence_hint": values.get("confidence_hint", 0.0),
                "notes": values.get("notes", ""),
                "active": values.get("active", True),
            }
        else:
            row_values = {
                "input_code": values.get("item_code", ""),
                "input_type": values.get("material_type") or values.get("plant_type") or values.get("crew_type") or values.get("notes", ""),
                "description": values.get("description", ""),
                "unit": values.get("unit", ""),
                "rate": values.get("rate", ""),
                "region": values.get("region", ""),
                "source": values.get("source", ""),
                "active": values.get("active", True),
            }

        append_row(target_sheet, target_headers, row_values)
        candidate_sheet.cell(row_number, positions["reviewer_status"]).value = "merged"
        write_review_log(
            workbook,
            {
                "timestamp": timestamp_now(),
                "boq_file": db_path,
                "sheet_name": target_sheet_name,
                "row_number": target_sheet.max_row,
                "boq_description": str(values.get("description") or ""),
                "decision": "candidate-merged",
                "matched_item_code": str(values.get("matched_item_code") or values.get("item_code") or ""),
                "matched_description": str(values.get("description") or ""),
                "confidence_score": safe_float(values.get("confidence_hint")) or 0.0,
                "reviewer_note": str(values.get("reviewer_note") or "Merged from CandidateMatches"),
            },
        )
        summary.merged += 1

    workbook.save(db_path)
    return summary

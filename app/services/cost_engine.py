"""Cloud-native BOQ pricing service backed by the real pricing engine."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from app.models.boq import BoqProcessingResponse, CostSummary, ParsedBoqItem
from app.services.file_parser import InvalidWorkbookError
from app.services.storage import download_gcs_uri, persist_artifacts
from src.cost_schema import schema_database_path
from src.config_loader import load_config
from src.engine import PricingEngine
from src.release_manager import current_production_database_path


LOGGER = logging.getLogger("boq_auto.api.cost_engine")
RUNTIME_DB_ROOT = Path("/tmp/boq_auto_runtime_db")


def process_boq_upload(file_bytes: bytes, filename: str, region: str) -> BoqProcessingResponse:
    """Price an uploaded BOQ using the existing workbook engine in a temp workspace."""
    if not file_bytes:
        raise InvalidWorkbookError("Uploaded workbook is empty.")

    config = load_config()
    db_path = _resolve_database_path(config)
    cloud_logger = logging.getLogger("boq_auto.api.engine")
    pricing_engine = PricingEngine(config, cloud_logger)
    request_id = uuid4().hex

    with TemporaryDirectory(prefix="boq_auto_api_") as temp_dir:
        temp_root = Path(temp_dir)
        input_path = temp_root / filename
        output_path = temp_root / f"{Path(filename).stem}_processed.xlsx"
        input_path.write_bytes(file_bytes)

        artifacts = pricing_engine.price_workbook(
            db_path=str(db_path),
            boq_path=str(input_path),
            output_path=str(output_path),
            region=region,
            apply_rates=True,
            matching_mode=str(config.get("matching.mode", "rule")),
        )

        workbook_bytes = output_path.read_bytes()
        items = _load_response_items(artifacts.audit_json)
        summary = _build_summary(items, artifacts, region, config.default_currency)
        stored = persist_artifacts(
            request_id=request_id,
            source_filename=filename,
            input_bytes=file_bytes,
            output_bytes=workbook_bytes,
            audit_json_path=artifacts.audit_json,
        )
        LOGGER.info(
            "processed_boq | filename=%s | db=%s | region=%s | items=%s | matched=%s | flagged=%s",
            filename,
            db_path,
            region,
            artifacts.processed,
            artifacts.matched,
            artifacts.flagged,
        )
        return BoqProcessingResponse(
            filename=filename,
            output_filename=output_path.name,
            region=region,
            summary=summary,
            items=items,
            database_path=str(db_path),
            input_storage_uri=stored.input_storage_uri,
            output_storage_uri=stored.output_storage_uri,
            audit_storage_uri=stored.audit_storage_uri,
            workbook_bytes=workbook_bytes,
        )


def _resolve_database_path(config) -> Path:
    override = os.getenv("BOQ_AUTO_API_DB_PATH", "").strip()
    gcs_override = os.getenv("BOQ_AUTO_API_DB_GCS_URI", "").strip()
    if gcs_override:
        return _resolve_gcs_database(gcs_override)
    if override:
        db_path = Path(override)
    else:
        db_path = current_production_database_path(config)
    if not db_path.exists():
        raise FileNotFoundError(f"Pricing database not found: {db_path}")
    return db_path


def _resolve_gcs_database(gcs_uri: str) -> Path:
    RUNTIME_DB_ROOT.mkdir(parents=True, exist_ok=True)
    filename = Path(gcs_uri.split("/", 3)[-1]).name
    local_db_path = RUNTIME_DB_ROOT / filename
    refresh = os.getenv("BOQ_AUTO_API_DB_REFRESH", "").strip().lower() in {"1", "true", "yes"}
    if refresh or not local_db_path.exists():
        download_gcs_uri(gcs_uri, local_db_path)

    sidecar_uri = os.getenv("BOQ_AUTO_API_DB_SIDECAR_GCS_URI", "").strip()
    if sidecar_uri:
        local_sidecar_path = schema_database_path(local_db_path)
        if refresh or not local_sidecar_path.exists():
            download_gcs_uri(sidecar_uri, local_sidecar_path)
    return local_db_path


def _load_response_items(audit_json_path: Path | None) -> list[ParsedBoqItem]:
    if audit_json_path is None or not audit_json_path.exists():
        return []
    payload = json.loads(audit_json_path.read_text(encoding="utf-8"))
    items: list[ParsedBoqItem] = []
    for row in payload.get("results", []):
        quantity = row.get("quantity")
        rate = row.get("rate")
        items.append(
            ParsedBoqItem(
                description=str(row.get("description") or ""),
                unit=str(row.get("unit") or ""),
                quantity=float(quantity) if quantity is not None else None,
                rate=float(rate) if rate is not None else None,
                amount=(float(quantity) * float(rate)) if quantity is not None and rate is not None else rate,
                sheet_name=str(row.get("sheet_name") or ""),
                row_number=int(row.get("row_number") or 0),
                decision=str(row.get("decision") or ""),
                matched_item_code=str(row.get("matched_item_code") or ""),
                matched_description=str(row.get("matched_description") or ""),
                confidence_score=float(row.get("confidence_score") or 0.0),
                review_flag=bool(row.get("review_flag") or False),
                basis_of_rate=str(row.get("basis_of_rate") or ""),
            )
        )
    return items


def _build_summary(items: list[ParsedBoqItem], artifacts, region: str, currency: str) -> CostSummary:
    priced_items = [item for item in items if item.rate is not None]
    total_cost = round(sum(item.amount or 0.0 for item in priced_items), 2)
    average_rate = round(sum(item.rate or 0.0 for item in priced_items) / len(priced_items), 2) if priced_items else 0.0
    quotation_summary = artifacts.quotation_summary
    return CostSummary(
        currency=quotation_summary.currency if quotation_summary else currency,
        region=region,
        item_count=artifacts.processed,
        priced_item_count=len(priced_items),
        matched_count=artifacts.matched,
        flagged_count=artifacts.flagged,
        total_cost=round(quotation_summary.grand_total, 2) if quotation_summary else total_cost,
        average_rate=average_rate,
    )

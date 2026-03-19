"""Helpers for the Streamlit internal app."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import shutil
from typing import Any
from uuid import uuid4

from src.config import load_config
from src.engine import PricingEngine
from src.logger import setup_logging
from src.release_manager import current_production_database_path, master_database_path
from src.tender_to_price import TenderToPriceRunner
from src.tender_workflow import TenderWorkflow
from src.utils import ensure_parent


@dataclass(slots=True)
class AppRuntime:
    """Shared runtime objects for the Streamlit UI."""

    config: Any
    logger: Any
    app_mode: str
    default_database_path: str
    master_database_path: str
    production_database_path: str
    pricing_engine: PricingEngine
    tender_workflow: TenderWorkflow
    tender_to_price_runner: TenderToPriceRunner


def resolve_default_database_path(config: Any, app_mode: str) -> Path:
    """Resolve the database path for the selected app mode."""

    if app_mode == "admin":
        return master_database_path(config)
    return current_production_database_path(config)


def build_runtime(config_path: str | None = None, app_mode: str | None = None) -> AppRuntime:
    """Create the shared runtime using existing config and logging."""

    config = load_config(config_path)
    logger = setup_logging(config.log_level, config.log_file)
    mode = (app_mode or str(config.get("ui.app_mode", "production"))).strip().lower() or "production"
    production_db = current_production_database_path(config)
    master_db = master_database_path(config)
    default_db = resolve_default_database_path(config, mode)
    pricing_engine = PricingEngine(config, logger)
    tender_workflow = TenderWorkflow(config, logger)
    tender_to_price_runner = TenderToPriceRunner(config, logger, tender_workflow=tender_workflow, pricing_engine=pricing_engine)
    return AppRuntime(
        config=config,
        logger=logger,
        app_mode=mode,
        default_database_path=str(default_db),
        master_database_path=str(master_db),
        production_database_path=str(production_db),
        pricing_engine=pricing_engine,
        tender_workflow=tender_workflow,
        tender_to_price_runner=tender_to_price_runner,
    )


def create_work_dir(config: Any) -> Path:
    """Create an isolated UI working directory under output."""

    root = Path(str(config.get("ui.work_root", str(Path(config.output_dir) / "ui_runs"))))
    root.mkdir(parents=True, exist_ok=True)
    work_dir = root / uuid4().hex
    work_dir.mkdir(parents=True, exist_ok=True)
    return work_dir


def save_uploaded_file(uploaded_file: Any, work_dir: Path) -> Path:
    """Persist a Streamlit uploaded file into the working directory."""

    destination = work_dir / uploaded_file.name
    ensure_parent(destination)
    destination.write_bytes(uploaded_file.getbuffer())
    return destination


def copy_into_work_dir(source_path: str, work_dir: Path) -> Path:
    """Copy an existing local file into the isolated working directory."""

    source = Path(source_path)
    if not source.exists():
        raise FileNotFoundError(f"File not found: {source}")
    destination = work_dir / source.name
    ensure_parent(destination)
    shutil.copy2(source, destination)
    return destination


def resolve_input_file(uploaded_file: Any | None, existing_path: str, work_dir: Path) -> Path:
    """Resolve an uploaded file or an existing repo path into the work area."""

    if uploaded_file is not None:
        return save_uploaded_file(uploaded_file, work_dir)
    if not existing_path.strip():
        raise ValueError("Please upload a file or provide an existing path.")
    return copy_into_work_dir(existing_path.strip(), work_dir)


def read_binary(path: str | Path) -> bytes:
    """Read file bytes for downloads."""

    return Path(path).read_bytes()


def tail_log(path: str | Path, line_count: int = 80) -> str:
    """Return a tail preview of the configured log file."""

    log_path = Path(path)
    if not log_path.exists():
        return "Log file not found."
    lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(lines[-line_count:])


def summarize_config(config: Any) -> dict[str, Any]:
    """Return a small config summary for the UI."""

    return {
        "app": config.data.get("app", {}),
        "paths": config.data.get("paths", {}),
        "matching": config.data.get("matching", {}),
        "ai": config.data.get("ai", {}),
        "processing": config.data.get("processing", {}),
        "commercial": config.data.get("commercial", {}),
        "tender_to_price": config.data.get("tender_to_price", {}),
        "ui": config.data.get("ui", {}),
        "database_release": config.data.get("database_release", {}),
    }


def safe_error_message(exc: Exception) -> str:
    """Convert a backend error into a UI-friendly message."""

    message = str(exc).strip()
    if not message:
        return "An unexpected error occurred while running the workflow."
    return message


def pretty_json(payload: Any) -> str:
    """Render JSON for preview widgets."""

    return json.dumps(payload, indent=2, ensure_ascii=True)


def read_json(path: str | Path) -> Any:
    """Read JSON payload from disk."""

    return json.loads(Path(path).read_text(encoding="utf-8"))

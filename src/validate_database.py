"""Compatibility wrapper for database validation."""

from __future__ import annotations

from .config import load_config
from .engine import PricingEngine
from .logger import setup_logging


def validate_database(db_path: str) -> list[str]:
    """Validate a BOQ AUTO pricing database workbook."""
    config = load_config()
    logger = setup_logging(config.log_level, config.log_file)
    engine = PricingEngine(config, logger)
    return engine.validate_database(db_path)

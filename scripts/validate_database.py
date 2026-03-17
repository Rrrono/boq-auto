"""Validate a BOQ AUTO database workbook."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import load_config
from src.engine import PricingEngine
from src.logger import setup_logging


def main() -> int:
    """Validate the provided database workbook."""
    parser = argparse.ArgumentParser(description="Validate BOQ AUTO database workbook")
    parser.add_argument("--db", default="database/qs_database.xlsx", help="Path to database workbook")
    args = parser.parse_args()

    config = load_config(str(PROJECT_ROOT / "config" / "default.yaml"))
    logger = setup_logging(config.log_level, config.log_file)
    engine = PricingEngine(config, logger)
    errors = engine.validate_database(args.db)
    if errors:
        for error in errors:
            print(error)
        return 1
    print(f"Database validation passed: {args.db}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

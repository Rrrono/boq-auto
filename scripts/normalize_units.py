"""Normalize units, regions, and normalized descriptions in the database."""

from __future__ import annotations

import argparse

from _ingestion_common import print_summary
from src.ingestion import normalize_database_units


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize units and regions in the database")
    parser.add_argument("--db", required=True)
    args = parser.parse_args()
    summary = normalize_database_units(args.db)
    print_summary(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

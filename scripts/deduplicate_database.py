"""Deactivate duplicate database entries."""

from __future__ import annotations

import argparse

from _ingestion_common import print_summary
from src.ingestion import deduplicate_database


def main() -> int:
    parser = argparse.ArgumentParser(description="Deduplicate a database sheet")
    parser.add_argument("--db", required=True)
    parser.add_argument("--sheet", default="RateLibrary")
    args = parser.parse_args()
    summary = deduplicate_database(args.db, args.sheet)
    print_summary(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Promote approved reviewed candidates into live database sheets."""

from __future__ import annotations

import argparse

from _ingestion_common import print_summary
from src.ingestion import promote_approved_candidates


def main() -> int:
    parser = argparse.ArgumentParser(description="Promote approved reviewed candidate rows")
    parser.add_argument("--db", required=True)
    parser.add_argument("--json", help="Optional training log JSON output")
    args = parser.parse_args()
    summary = promote_approved_candidates(args.db, args.json)
    print_summary(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

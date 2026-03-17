"""Generate a Candidate Review sheet and optional training JSON."""

from __future__ import annotations

import argparse

from _ingestion_common import print_summary
from src.ingestion import generate_review_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a candidate review report")
    parser.add_argument("--db", required=True)
    parser.add_argument("--json", help="Optional training log JSON output")
    args = parser.parse_args()
    summary = generate_review_report(args.db, args.json)
    print_summary(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

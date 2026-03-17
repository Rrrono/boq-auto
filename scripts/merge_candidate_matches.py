"""Merge approved CandidateMatches into the live database sheets."""

from __future__ import annotations

import argparse

from _ingestion_common import print_summary
from src.ingestion import merge_candidate_matches


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge approved CandidateMatches")
    parser.add_argument("--db", required=True)
    args = parser.parse_args()
    summary = merge_candidate_matches(args.db)
    print_summary(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

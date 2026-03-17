"""Merge Candidate Review decisions back into CandidateMatches."""

from __future__ import annotations

import argparse

from _ingestion_common import print_summary
from src.ingestion import merge_reviewed_candidates


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge reviewed decisions into CandidateMatches")
    parser.add_argument("--db", required=True)
    parser.add_argument("--reviewer", help="Fallback reviewer name")
    args = parser.parse_args()
    summary = merge_reviewed_candidates(args.db, args.reviewer)
    print_summary(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

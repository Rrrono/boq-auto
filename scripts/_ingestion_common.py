"""Shared helpers for ingestion scripts."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def print_summary(summary) -> None:
    """Render a short import summary to stdout."""
    print(f"target_sheet={summary.target_sheet}")
    print(f"source_file={summary.source_file}")
    print(f"total_rows={summary.total_rows}")
    print(f"appended={summary.appended}")
    print(f"skipped_duplicates={summary.skipped_duplicates}")
    print(f"candidates_created={summary.candidates_created}")
    print(f"merged={summary.merged}")
    print(f"normalized_rows={summary.normalized_rows}")
    print(f"reviewed={summary.reviewed}")
    print(f"rejected={summary.rejected}")
    print(f"promoted={summary.promoted}")
    print(f"report_rows={summary.report_rows}")
    print(f"training_records={summary.training_records}")
    if summary.notes:
        print("notes=" + " | ".join(summary.notes))

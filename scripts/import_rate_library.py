"""Import structured rate rows into RateLibrary."""

from __future__ import annotations

import argparse

from _ingestion_common import print_summary
from src.ingestion import build_rate_library_row, import_structured_rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Import structured data into RateLibrary")
    parser.add_argument("--db", required=True, help="Path to database workbook")
    parser.add_argument("--input", required=True, help="CSV or Excel file to import")
    parser.add_argument("--sheet", help="Source worksheet name for Excel imports")
    parser.add_argument("--section", help="Default section")
    parser.add_argument("--subsection", help="Default subsection")
    parser.add_argument("--region", help="Default region")
    parser.add_argument("--source", help="Default source label")
    args = parser.parse_args()

    summary = import_structured_rows(
        db_path=args.db,
        input_path=args.input,
        target_sheet="RateLibrary",
        mapper=build_rate_library_row,
        defaults={
            "section": args.section,
            "subsection": args.subsection,
            "region": args.region,
            "source": args.source,
        },
        source_sheet=args.sheet,
    )
    print_summary(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

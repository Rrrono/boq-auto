"""Import labour-focused rate rows into RateLibrary."""

from __future__ import annotations

import argparse

from _ingestion_common import print_summary
from src.ingestion import build_rate_library_row, import_structured_rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Import labour rates into RateLibrary")
    parser.add_argument("--db", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--sheet")
    parser.add_argument("--section", default="Dayworks")
    parser.add_argument("--crew-type", default="labour")
    parser.add_argument("--region")
    parser.add_argument("--source")
    args = parser.parse_args()

    summary = import_structured_rows(
        db_path=args.db,
        input_path=args.input,
        target_sheet="RateLibrary",
        mapper=build_rate_library_row,
        defaults={
            "section": args.section,
            "crew_type": args.crew_type,
            "region": args.region,
            "source": args.source,
        },
        source_sheet=args.sheet,
    )
    print_summary(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

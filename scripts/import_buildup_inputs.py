"""Import structured rows into BuildUpInputs."""

from __future__ import annotations

import argparse

from _ingestion_common import print_summary
from src.ingestion import build_buildup_input_row, import_structured_rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Import build-up inputs")
    parser.add_argument("--db", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--sheet")
    parser.add_argument("--input-type")
    parser.add_argument("--region")
    parser.add_argument("--source")
    args = parser.parse_args()

    summary = import_structured_rows(
        db_path=args.db,
        input_path=args.input,
        target_sheet="BuildUpInputs",
        mapper=build_buildup_input_row,
        defaults={
            "input_type": args.input_type,
            "region": args.region,
            "source": args.source,
        },
        source_sheet=args.sheet,
    )
    print_summary(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

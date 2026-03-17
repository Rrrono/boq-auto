"""CLI for BOQ AUTO."""

from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(prog="python -m src.main", description="BOQ AUTO pricing engine")
    parser.add_argument("--config", help="Path to YAML or JSON config file")

    subparsers = parser.add_subparsers(dest="command", required=True)

    price = subparsers.add_parser("price", help="Price a single BOQ workbook")
    price.add_argument("--db", required=True, help="Path to database workbook")
    price.add_argument("--boq", required=True, help="Path to BOQ workbook")
    price.add_argument("--out", required=True, help="Path to output workbook")
    price.add_argument("--region", help="Region preference, e.g. Nyanza")
    price.add_argument("--threshold", type=float, help="Matching threshold")
    price.add_argument("--apply", action="store_true", help="Write rates back into the BOQ")
    price.add_argument("--desc-col", type=int, help="Override description column index")
    price.add_argument("--unit-col", type=int, help="Override unit column index")
    price.add_argument("--qty-col", type=int, help="Override quantity column index")
    price.add_argument("--rate-col", type=int, help="Override rate column index")
    price.add_argument("--amount-col", type=int, help="Override amount column index")

    batch = subparsers.add_parser("batch", help="Price all BOQs in a folder")
    batch.add_argument("--db", required=True, help="Path to database workbook")
    batch.add_argument("--boq-dir", required=True, help="Folder containing BOQ workbooks")
    batch.add_argument("--out-dir", required=True, help="Folder for priced workbooks")
    batch.add_argument("--region", help="Region preference")
    batch.add_argument("--threshold", type=float, help="Matching threshold")
    batch.add_argument("--apply", action="store_true", help="Write rates back into the BOQ")

    validate = subparsers.add_parser("validate-db", help="Validate the database workbook")
    validate.add_argument("--db", required=True, help="Path to database workbook")

    unmatched = subparsers.add_parser("export-unmatched", help="Export unmatched lines from a priced workbook")
    unmatched.add_argument("--input", required=True, help="Path to priced workbook")
    unmatched.add_argument("--csv", required=True, help="Output CSV path")

    import_rates = subparsers.add_parser("import-rates", help="Import structured rate data into the database")
    import_rates.add_argument("--db", required=True, help="Path to database workbook")
    import_rates.add_argument("--input", required=True, help="CSV or Excel source file")
    import_rates.add_argument("--sheet", help="Source worksheet for Excel imports")
    import_rates.add_argument("--kind", choices=["rate-library", "materials", "labour", "plant", "buildup-inputs"], default="rate-library")
    import_rates.add_argument("--section", help="Default section")
    import_rates.add_argument("--subsection", help="Default subsection")
    import_rates.add_argument("--region", help="Default region")
    import_rates.add_argument("--source", help="Default source label")
    import_rates.add_argument("--material-type", help="Default material type")
    import_rates.add_argument("--crew-type", help="Default crew type")
    import_rates.add_argument("--plant-type", help="Default plant type")
    import_rates.add_argument("--input-type", help="Default build-up input type")

    merge = subparsers.add_parser("merge-candidates", help="Merge approved CandidateMatches into live sheets")
    merge.add_argument("--db", required=True, help="Path to database workbook")

    normalize = subparsers.add_parser("normalize-units", help="Normalize units and regions in the database")
    normalize.add_argument("--db", required=True, help="Path to database workbook")

    dedupe = subparsers.add_parser("deduplicate-db", help="Deactivate duplicate database rows")
    dedupe.add_argument("--db", required=True, help="Path to database workbook")
    dedupe.add_argument("--sheet", default="RateLibrary", help="Database sheet to deduplicate")

    review_report = subparsers.add_parser("review-report", help="Generate Candidate Review sheet and optional training JSON")
    review_report.add_argument("--db", required=True, help="Path to database workbook")
    review_report.add_argument("--json", help="Optional training log JSON output")

    merge_reviewed = subparsers.add_parser("merge-reviewed", help="Merge Candidate Review decisions back into CandidateMatches")
    merge_reviewed.add_argument("--db", required=True, help="Path to database workbook")
    merge_reviewed.add_argument("--reviewer", help="Fallback reviewer name")

    promote = subparsers.add_parser("promote-approved", help="Promote approved reviewed candidates into live sheets")
    promote.add_argument("--db", required=True, help="Path to database workbook")
    promote.add_argument("--json", help="Optional training log JSON output")

    return parser

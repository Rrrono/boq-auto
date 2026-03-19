"""CLI for BOQ AUTO."""

from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(prog="python -m src.main", description="BOQ AUTO pricing and tender analysis")
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

    analyze_tender = subparsers.add_parser("analyze-tender", help="Analyze a tender text input and generate a review workbook")
    analyze_tender.add_argument("--input", required=True, help="Path to local tender text, PDF, CSV, or Excel input")
    analyze_tender.add_argument("--out", required=True, help="Output workbook path")
    analyze_tender.add_argument("--json", help="Optional JSON analysis export path")
    analyze_tender.add_argument("--title", help="Optional tender title override")

    tender_checklist = subparsers.add_parser("tender-checklist", help="Generate a tender checklist workbook from a tender input")
    tender_checklist.add_argument("--input", required=True, help="Path to local tender text, PDF, CSV, or Excel input")
    tender_checklist.add_argument("--out", required=True, help="Output workbook path")
    tender_checklist.add_argument("--json", help="Optional JSON analysis export path")
    tender_checklist.add_argument("--title", help="Optional tender title override")

    gap_check = subparsers.add_parser("gap-check", help="Compare tender scope against an optional BOQ and produce a review-first gap report")
    gap_check.add_argument("--input", required=True, help="Path to local tender text, PDF, CSV, or Excel input")
    gap_check.add_argument("--out", required=True, help="Output workbook path")
    gap_check.add_argument("--boq", help="Optional BOQ workbook to compare against the tender scope")
    gap_check.add_argument("--json", help="Optional JSON analysis export path")
    gap_check.add_argument("--title", help="Optional tender title override")

    draft_boq = subparsers.add_parser("draft-boq", help="Generate draft BOQ suggestions from tender text")
    draft_boq.add_argument("--input", required=True, help="Path to local tender text, PDF, CSV, or Excel input")
    draft_boq.add_argument("--out", required=True, help="Output workbook path")
    draft_boq.add_argument("--json", help="Optional JSON analysis export path")
    draft_boq.add_argument("--title", help="Optional tender title override")

    tender_price = subparsers.add_parser("tender-price", help="Run the integrated tender-analysis to pricing workflow")
    tender_price.add_argument("--input", required=True, help="Path to local tender text, PDF, CSV, or Excel input")
    tender_price.add_argument("--db", required=True, help="Path to database workbook")
    tender_price.add_argument("--out", required=True, help="Output workbook path")
    tender_price.add_argument("--boq", help="Optional BOQ workbook to price and compare against")
    tender_price.add_argument("--json", help="Optional integrated JSON export path")
    tender_price.add_argument("--region", help="Region preference")
    tender_price.add_argument("--threshold", type=float, help="Matching threshold")
    tender_price.add_argument("--apply", action="store_true", help="Write rates back into priced sheets")
    tender_price.add_argument("--title", help="Optional tender title override")

    return parser

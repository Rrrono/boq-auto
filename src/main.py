"""Entry point for BOQ AUTO."""

from __future__ import annotations

from argparse import Namespace

from .audit import export_unmatched_from_workbook
from .batch_runner import run_batch
from .cli import build_parser
from .config import load_config, merge_cli_overrides
from .engine import PricingEngine
from .ingestion import (
    build_buildup_input_row,
    build_rate_library_row,
    deduplicate_database,
    generate_review_report,
    import_priced_boq,
    import_structured_rows,
    merge_candidate_matches,
    merge_reviewed_candidates,
    normalize_database_units,
    promote_approved_candidates,
    sync_review_artifacts_to_candidate_matches,
)
from .logger import setup_logging
from .tender_to_price import TenderToPriceRunner
from .tender_workflow import TenderWorkflow


def _build_runtime(args: Namespace) -> tuple:
    config = load_config(args.config)
    config = merge_cli_overrides(config, {"processing.apply_rates": getattr(args, "apply", None) or None})
    logger = setup_logging(config.log_level, config.log_file)
    return config, logger


def _build_engine(config, logger) -> PricingEngine:
    return PricingEngine(config, logger)


def _handle_price(engine: PricingEngine, logger, args: Namespace) -> int:
    artifacts = engine.price_workbook(
        db_path=args.db,
        boq_path=args.boq,
        output_path=args.out,
        region=args.region,
        threshold=args.threshold,
        apply_rates=args.apply,
        column_overrides={
            "description_col": args.desc_col,
            "unit_col": args.unit_col,
            "quantity_col": args.qty_col,
            "rate_col": args.rate_col,
            "amount_col": args.amount_col,
        },
    )
    logger.info(
        "Processed %s items with %s matched and %s flagged. Output: %s",
        artifacts.processed,
        artifacts.matched,
        artifacts.flagged,
        artifacts.output_workbook,
    )
    return 0


def _handle_batch(engine: PricingEngine, logger, args: Namespace) -> int:
    artifacts = run_batch(
        engine=engine,
        db_path=args.db,
        boq_dir=args.boq_dir,
        out_dir=args.out_dir,
        region=args.region,
        threshold=args.threshold,
        apply_rates=args.apply,
    )
    logger.info("Batch complete. Generated %s priced workbook(s).", len(artifacts))
    return 0


def _handle_validate(engine: PricingEngine, logger, args: Namespace) -> int:
    errors = engine.validate_database(args.db)
    if errors:
        for error in errors:
            logger.error(error)
        return 1
    logger.info("Database validation passed for %s", args.db)
    return 0


def _handle_import(logger, args: Namespace) -> int:
    kind_defaults = {
        "rate-library": ("RateLibrary", build_rate_library_row, {"section": args.section, "subsection": args.subsection, "region": args.region, "source": args.source}),
        "materials": ("RateLibrary", build_rate_library_row, {"section": args.section or "Materials", "material_type": args.material_type or "general", "region": args.region, "source": args.source}),
        "labour": ("RateLibrary", build_rate_library_row, {"section": args.section or "Dayworks", "crew_type": args.crew_type or "labour", "region": args.region, "source": args.source}),
        "plant": ("RateLibrary", build_rate_library_row, {"section": args.section or "Dayworks", "plant_type": args.plant_type or "plant", "region": args.region, "source": args.source}),
        "buildup-inputs": ("BuildUpInputs", build_buildup_input_row, {"input_type": args.input_type, "region": args.region, "source": args.source}),
    }
    target_sheet, mapper, defaults = kind_defaults[args.kind]
    summary = import_structured_rows(args.db, args.input, target_sheet, mapper, defaults=defaults, source_sheet=args.sheet)
    logger.info(
        "Imported %s rows into %s: appended=%s duplicates=%s candidates=%s",
        summary.total_rows,
        summary.target_sheet,
        summary.appended,
        summary.skipped_duplicates,
        summary.candidates_created,
    )
    return 0


def _handle_import_priced_boq(logger, args: Namespace) -> int:
    summary = import_priced_boq(
        db_path=args.db,
        boq_path=args.input,
        region=args.region,
        source_label=args.source,
        ai_assist=args.ai_assist,
        column_overrides={
            "description_col": args.desc_col,
            "unit_col": args.unit_col,
            "quantity_col": args.qty_col,
            "rate_col": args.rate_col,
            "amount_col": args.amount_col,
        },
    )
    logger.info(
        "Imported priced BOQ rows: extracted=%s appended=%s candidates=%s duplicates=%s notes=%s",
        summary.total_rows,
        summary.appended,
        summary.candidates_created,
        summary.skipped_duplicates,
        "; ".join(summary.notes),
    )
    return 0


def _handle_tender(workflow: TenderWorkflow, logger, args: Namespace, checklist_only: bool = False) -> int:
    runner = workflow.generate_checklist if checklist_only else workflow.analyze
    result = runner(
        input_path=args.input,
        output_path=args.out,
        json_path=args.json,
        title_override=args.title,
    )
    logger.info(
        "Tender analysis complete for %s: requirements=%s scope_sections=%s workbook=%s",
        result.document.document_name,
        len(result.requirements),
        len(result.scope_sections),
        result.output_workbook,
    )
    return 0


def _handle_gap_check(workflow: TenderWorkflow, logger, args: Namespace) -> int:
    result = workflow.gap_check(
        input_path=args.input,
        output_path=args.out,
        boq_path=args.boq,
        json_path=args.json,
        title_override=args.title,
    )
    logger.info(
        "Gap check complete for %s: gap_items=%s clarifications=%s workbook=%s",
        result.document.document_name,
        len(result.gap_items),
        len(result.clarifications),
        result.output_workbook,
    )
    return 0


def _handle_draft_boq(workflow: TenderWorkflow, logger, args: Namespace) -> int:
    result = workflow.draft_boq(
        input_path=args.input,
        output_path=args.out,
        json_path=args.json,
        title_override=args.title,
    )
    logger.info(
        "Draft BOQ generation complete for %s: suggestions=%s clarifications=%s workbook=%s",
        result.document.document_name,
        len(result.draft_suggestions),
        len(result.clarifications),
        result.output_workbook,
    )
    return 0


def _handle_tender_price(config, logger, args: Namespace) -> int:
    runner = TenderToPriceRunner(config, logger)
    artifacts = runner.run(
        input_path=args.input,
        db_path=args.db,
        output_path=args.out,
        boq_path=args.boq,
        region=args.region,
        threshold=args.threshold,
        apply_rates=args.apply,
        title_override=args.title,
        json_path=args.json,
    )
    logger.info(
        "Tender-price complete: workbook=%s handoff_rows=%s priced_items=%s",
        artifacts.output_workbook,
        len(artifacts.pricing_handoff_rows),
        artifacts.pricing_artifacts.processed if artifacts.pricing_artifacts else 0,
    )
    return 0


def main() -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()
    config, logger = _build_runtime(args)

    if args.command == "price":
        engine = _build_engine(config, logger)
        return _handle_price(engine, logger, args)
    if args.command == "batch":
        engine = _build_engine(config, logger)
        return _handle_batch(engine, logger, args)
    if args.command == "validate-db":
        engine = _build_engine(config, logger)
        return _handle_validate(engine, logger, args)
    if args.command == "export-unmatched":
        output = export_unmatched_from_workbook(args.input, args.csv)
        logger.info("Exported unmatched lines to %s", output)
        return 0
    if args.command == "import-rates":
        return _handle_import(logger, args)
    if args.command == "import-priced-boq":
        return _handle_import_priced_boq(logger, args)
    if args.command == "merge-candidates":
        summary = merge_candidate_matches(args.db)
        logger.info("Merged %s approved candidate row(s).", summary.merged)
        return 0
    if args.command == "normalize-units":
        summary = normalize_database_units(args.db)
        logger.info("Normalized %s database field(s).", summary.normalized_rows)
        return 0
    if args.command == "deduplicate-db":
        summary = deduplicate_database(args.db, args.sheet)
        logger.info("Deactivated %s duplicate row(s) in %s.", summary.skipped_duplicates, args.sheet)
        return 0
    if args.command == "review-report":
        summary = generate_review_report(args.db, args.json)
        logger.info("Generated Candidate Review sheet with %s row(s).", summary.report_rows)
        return 0
    if args.command == "merge-reviewed":
        summary = merge_reviewed_candidates(args.db, args.reviewer)
        logger.info("Merged %s reviewed approval(s) and %s rejection(s).", summary.reviewed, summary.rejected)
        return 0
    if args.command == "promote-approved":
        summary = promote_approved_candidates(args.db, args.json)
        logger.info("Promoted %s approved reviewed row(s).", summary.promoted)
        return 0
    if args.command == "sync-review-artifacts":
        summary = sync_review_artifacts_to_candidate_matches(args.db, args.schema)
        logger.info(
            "Synced %s normalized reviewer artifact(s) into CandidateMatches (%s duplicate marker(s) skipped).",
            summary.appended,
            summary.skipped_duplicates,
        )
        if args.refresh_review_report:
            report_summary = generate_review_report(args.db)
            logger.info("Refreshed Candidate Review sheet with %s row(s).", report_summary.report_rows)
        return 0
    if args.command == "analyze-tender":
        workflow = TenderWorkflow(config, logger)
        return _handle_tender(workflow, logger, args)
    if args.command == "tender-checklist":
        workflow = TenderWorkflow(config, logger)
        return _handle_tender(workflow, logger, args, checklist_only=True)
    if args.command == "gap-check":
        workflow = TenderWorkflow(config, logger)
        return _handle_gap_check(workflow, logger, args)
    if args.command == "draft-boq":
        workflow = TenderWorkflow(config, logger)
        return _handle_draft_boq(workflow, logger, args)
    if args.command == "tender-price":
        return _handle_tender_price(config, logger, args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

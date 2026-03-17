# BOQ AUTO

Local Python application for pricing Kenyan construction BOQs from an Excel-based rate library.

## Features

- Prices Excel BOQs using an Excel database workbook
- Detects likely BOQ columns automatically, with CLI/config overrides
- Uses text normalization, aliases, fuzzy matching, section inference, and unit checks
- Handles messy BOQ workbooks with heading-aware section detection, summary-sheet skipping, merged-cell resilience, subtotal detection, and non-standard column layouts
- Falls back to build-up recipes when direct library matches are weak
- Preserves the source BOQ workbook structure and writes an additional `Match Suggestions` sheet
- Supports batch processing, database validation, unmatched export, and audit JSON output
- Produces commercial quotation outputs including section totals, markups, VAT, assumptions, exclusions, basis-of-rate reporting, and commercial review sheets
- Supports estimator learning through Candidate Review sheets, approved/rejected review workflows, promotions into `Aliases` and `RateLibrary`, and training-log JSON exports
- Works locally on Windows with Python 3.11+

## Windows Setup

1. Open PowerShell in this project folder.
2. Create and activate a virtual environment:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
```

3. Install dependencies:

```powershell
py -3.11 -m pip install --upgrade pip
py -3.11 -m pip install -r requirements.txt
```

Project overview:

- [docs/project_overview.md](C:/Users/Ronoz/Documents/BOSCO%20CONSULT/BOQ%20AUTO/docs/project_overview.md)
- [docs/workflows.md](C:/Users/Ronoz/Documents/BOSCO%20CONSULT/BOQ%20AUTO/docs/workflows.md)

## First Run

Generate the demo database workbook:

```powershell
py -3.11 scripts\create_demo_database.py
```

Generate the demo BOQ workbook:

```powershell
py -3.11 scripts\create_demo_boq.py
```

Validate the database:

```powershell
py -3.11 -m src.main validate-db --db database\qs_database.xlsx
```

Price the demo BOQ:

```powershell
py -3.11 -m src.main price --db database\qs_database.xlsx --boq boq\demo_boq.xlsx --out output\priced_demo.xlsx --apply --region Nyanza --threshold 78
```

## Batch Pricing

The priced workbook now includes these additional quotation sheets:

- `Quotation Summary`
- `Assumptions`
- `Exclusions`
- `Basis of Rates`
- `Commercial Review`
- `Match Suggestions`

Export unmatched items from the priced workbook:

```powershell
py -3.11 -m src.main export-unmatched --input output\priced_demo.xlsx --csv output\unmatched.csv
```

```powershell
py -3.11 -m src.main batch --db database\qs_database.xlsx --boq-dir boq --out-dir output --apply --region Nyanza
```

## Review Cycle

Generate the review queue and JSON training snapshot:

```powershell
py -3.11 scripts\review_report.py --db database\qs_database.xlsx --json output\review_training_log.json
```

Merge estimator review decisions back into `CandidateMatches`:

```powershell
py -3.11 scripts\merge_reviewed.py --db database\qs_database.xlsx --reviewer "Senior QS"
```

Promote approved reviewed records into live learning targets:

```powershell
py -3.11 scripts\promote_approved.py --db database\qs_database.xlsx --json output\promotion_training_log.json
```

## Import Cycle

Normalize and clean before or after imports:

```powershell
py -3.11 scripts\normalize_units.py --db database\qs_database.xlsx
py -3.11 scripts\deduplicate_database.py --db database\qs_database.xlsx --sheet RateLibrary
```

Import into the live library:

```powershell
py -3.11 scripts\import_rate_library.py --db database\qs_database.xlsx --input templates\rate_library_import_template.csv --section Materials --region Nyanza --source "Manual Template"
```

Specialized imports:

```powershell
py -3.11 scripts\import_materials.py --db database\qs_database.xlsx --input incoming\materials.csv --section Materials --material-type cement --region Nyanza
py -3.11 scripts\import_labour.py --db database\qs_database.xlsx --input incoming\labour.xlsx --sheet Rates --crew-type artisans --region Nairobi
py -3.11 scripts\import_plant.py --db database\qs_database.xlsx --input incoming\plant.csv --plant-type earthmoving --region Nyanza
py -3.11 scripts\import_buildup_inputs.py --db database\qs_database.xlsx --input incoming\buildup_inputs.csv --input-type material --region Nyanza
```

Merge reviewed candidate imports:

```powershell
py -3.11 scripts\merge_candidate_matches.py --db database\qs_database.xlsx
```

## Test Run

Run tests:

```powershell
py -3.11 -m pytest
```

Equivalent CLI commands are also available through `python -m src.main`:

```powershell
py -3.11 -m src.main import-rates --db database\qs_database.xlsx --input templates\rate_library_import_template.csv --kind rate-library --section Materials --region Nyanza
py -3.11 -m src.main merge-candidates --db database\qs_database.xlsx
py -3.11 -m src.main normalize-units --db database\qs_database.xlsx
py -3.11 -m src.main deduplicate-db --db database\qs_database.xlsx --sheet RateLibrary
py -3.11 -m src.main review-report --db database\qs_database.xlsx --json output\review_training_log.json
py -3.11 -m src.main merge-reviewed --db database\qs_database.xlsx --reviewer "Senior QS"
py -3.11 -m src.main promote-approved --db database\qs_database.xlsx --json output\promotion_training_log.json
```

## Notes

- Input BOQs go in [boq](C:/Users/Ronoz/Documents/BOSCO%20CONSULT/BOQ%20AUTO/boq).
- The pricing database workbook goes in [database](C:/Users/Ronoz/Documents/BOSCO%20CONSULT/BOQ%20AUTO/database).
- Output workbooks, unmatched CSVs, and audit JSON files go in [output](C:/Users/Ronoz/Documents/BOSCO%20CONSULT/BOQ%20AUTO/output).
- Logs are written to [logs](C:/Users/Ronoz/Documents/BOSCO%20CONSULT/BOQ%20AUTO/logs).
- Commercial markups default from [config/default.yaml](C:/Users/Ronoz/Documents/BOSCO%20CONSULT/BOQ%20AUTO/config/default.yaml) and can also be supplied by the database `Controls` sheet.
- Human review is still required for low-confidence matches, build-up fallbacks, and lines with alternate commercial options.
- The ingestion subsystem uses `CandidateMatches` for uncertain imports and writes approved merges into `ReviewLog`.
- The estimator learning loop uses `Candidate Review` as the editable team worksheet, then syncs decisions back into `CandidateMatches`, `Aliases`, `RateLibrary`, and timestamped `ReviewLog` entries.
- Additional step-by-step ingestion notes are in [docs/workflows.md](C:/Users/Ronoz/Documents/BOSCO%20CONSULT/BOQ%20AUTO/docs/workflows.md).

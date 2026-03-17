# Workflows

## Tender Analysis Workflow

1. Place a local tender text file, normalized extracted PDF text file, CSV export, or Excel-derived structured text workbook in [tender](C:/Users/Ronoz/Documents/BOSCO%20CONSULT/BOQ%20AUTO/tender).
2. Run Tender Analysis:

```powershell
py -3.11 -m src.main analyze-tender --input tender\demo_tender_notice.txt --out output\tender_analysis_demo.xlsx --json output\tender_analysis_demo.json
```

3. Review the output workbook sheets:
   - `Tender Analysis Summary`
   - `Tender Checklist`
   - `Scope Summary`
   - `Extracted Requirements`
4. Confirm mandatory submission items, securities, meetings, periods, pricing instructions, and technical-compliance items.
5. Use the extracted scope summary and pricing instructions as the hand-off input for later BOQ gap checking and pricing.

Checklist-focused command:

```powershell
py -3.11 -m src.main tender-checklist --input tender\demo_tender_notice.txt --out output\tender_checklist_demo.xlsx
```

## Tender Analysis v2 Workflow

1. Run draft BOQ generation from tender scope text:

```powershell
py -3.11 -m src.main draft-boq --input tender\demo_tender_scope_only.txt --out output\draft_boq_demo.xlsx --json output\draft_boq_demo.json
```

2. Review:
   - `Draft BOQ Suggestions`
   - `Clarification Log`
3. Confirm missing measurements, provisional wording, and unusual requirements before building a working BOQ.

4. If a BOQ exists, run a tender-vs-BOQ gap check:

```powershell
py -3.11 -m src.main gap-check --input tender\demo_tender_notice.txt --boq boq\demo_boq.xlsx --out output\gap_check_demo.xlsx --json output\gap_check_demo.json
```

5. Review:
   - `BOQ Gap Report`
   - `Draft BOQ Suggestions`
   - `Clarification Log`
6. Treat all gap findings as review-first. They are prompts for estimator/QS judgment, not final omissions.

## Tender To Pricing Workflow

1. Tender only mode:

```powershell
py -3.11 -m src.main tender-price --input tender\demo_tender_scope_only.txt --db database\qs_database.xlsx --out output\tender_only_priced.xlsx --region Nyanza --threshold 78 --json output\tender_only_priced.json
```

This creates:
- `Pricing Handoff` with tender-drafted rows only
- pricing-engine outputs such as `Match Suggestions`, `Quotation Summary`, `Assumptions`, and `Exclusions`
- tender-analysis review sheets such as `Tender Analysis Summary`, `BOQ Gap Report`, and `Clarification Log`

2. Tender plus BOQ mode:

```powershell
py -3.11 -m src.main tender-price --input tender\demo_tender_notice.txt --db database\qs_database.xlsx --boq boq\demo_boq.xlsx --out output\tender_priced_demo.xlsx --apply --region Nyanza --threshold 78 --json output\tender_priced_demo.json
```

This:
- prices the supplied BOQ with the existing pricing engine
- adds `Pricing Handoff` as a review sheet
- appends tender-analysis, gap-check, draft BOQ, and clarification sheets into the priced workbook

3. Review-first rules:
- no quantities are fabricated for tender-drafted rows
- tender-drafted and gap-derived handoff rows remain flagged for review
- existing BOQ rows are marked separately from tender-derived rows in `Pricing Handoff`

## Rate Ingestion Workflow

1. Prepare a structured source file in CSV or Excel format.
2. Start from [templates/rate_library_import_template.csv](C:/Users/Ronoz/Documents/BOSCO%20CONSULT/BOQ%20AUTO/templates/rate_library_import_template.csv) when possible.
3. Import the source into the live database:

```powershell
py -3.11 scripts\import_rate_library.py --db database\qs_database.xlsx --input templates\rate_library_import_template.csv --section Materials --region Nyanza --source "Manual Template"
```

4. Review any uncertain imports in the `CandidateMatches` sheet.
5. Mark rows in `CandidateMatches.reviewer_status` as `approved`, `approve_append`, or `approve_update` when ready.
6. Merge approved rows:

```powershell
py -3.11 scripts\merge_candidate_matches.py --db database\qs_database.xlsx
```

7. Normalize and clean the database:

```powershell
py -3.11 scripts\normalize_units.py --db database\qs_database.xlsx
py -3.11 scripts\deduplicate_database.py --db database\qs_database.xlsx --sheet RateLibrary
```

## Specialized Imports

Materials:

```powershell
py -3.11 scripts\import_materials.py --db database\qs_database.xlsx --input incoming\materials.csv --section Materials --material-type cement --region Nyanza
```

Labour:

```powershell
py -3.11 scripts\import_labour.py --db database\qs_database.xlsx --input incoming\labour.xlsx --sheet Rates --crew-type artisans --region Nairobi
```

Plant:

```powershell
py -3.11 scripts\import_plant.py --db database\qs_database.xlsx --input incoming\plant.csv --plant-type earthmoving --region Nyanza
```

Build-up inputs:

```powershell
py -3.11 scripts\import_buildup_inputs.py --db database\qs_database.xlsx --input incoming\buildup_inputs.csv --input-type material --region Nyanza
```

## Review Rules

- Exact duplicates are skipped where the existing rate is materially the same.
- Duplicates with conflicting rates or metadata are sent to `CandidateMatches`.
- Every approved merge is written into `ReviewLog`.
- Human review is required before merging `CandidateMatches` rows into the live library.

## Estimator Review And Learning Workflow

1. Generate the review workbook sheet and a machine-readable learning snapshot:

```powershell
py -3.11 scripts\review_report.py --db database\qs_database.xlsx --json output\review_training_log.json
```

2. Open the database workbook and review the `Candidate Review` sheet.
3. For each row, update these fields as needed:
   - `reviewer_status`: `approved`, `rejected`, or leave `pending`
   - `review_decision`: practical decision such as `accept`, `reject`, `hold`, `revise-rate`
   - `promote_target`: `aliases`, `ratelibrary`, or `candidatematches`
   - `approved_item_code`, `approved_description`, `approved_rate`, `approved_canonical_term`
   - `confidence_override` when the estimator intentionally overrides import confidence
   - `reviewer_note` with the commercial or technical reason
4. Merge the sheet decisions back into `CandidateMatches`:

```powershell
py -3.11 scripts\merge_reviewed.py --db database\qs_database.xlsx --reviewer "Senior QS"
```

5. Promote approved reviewed rows into the selected live destination and export a learning log:

```powershell
py -3.11 scripts\promote_approved.py --db database\qs_database.xlsx --json output\promotion_training_log.json
```

6. Re-run `review_report.py` whenever the team wants a refreshed queue and training export.

## Practical Team Notes

- Use `aliases` when the estimator confirms that site wording should map to an existing canonical term.
- Use `ratelibrary` when the estimator has approved a rate that should become a live reusable database row.
- Use `candidatematches` when the team wants to preserve the reviewed decision without promoting it into the live commercial library yet.
- `ReviewLog` acts as the timestamped audit trail for approvals, rejections, promotions, and confidence overrides.

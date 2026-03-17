# Workflows

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

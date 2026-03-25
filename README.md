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
- Includes Tender Analysis v1 for tender text review, requirement extraction, submission checklist generation, scope parsing, and tender-analysis summary output
- Supports tender PDF ingestion with direct text extraction and OCR fallback for scanned PDFs
- Generates synthesized review-first Draft BOQ Suggestions that consolidate measurable work instead of dumping raw tender clauses
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

If you want OCR fallback for scanned PDFs, install Tesseract OCR on Windows and confirm the executable path matches `config/default.yaml`:

```yaml
tesseract_path: "C:/Program Files/Tesseract-OCR/tesseract.exe"
```

Project overview:

- [docs/project_overview.md](C:/Users/Ronoz/Documents/BOSCO%20CONSULT/BOQ%20AUTO/docs/project_overview.md)
- [docs/workflows.md](C:/Users/Ronoz/Documents/BOSCO%20CONSULT/BOQ%20AUTO/docs/workflows.md)
- Demo tender inputs: [tender](C:/Users/Ronoz/Documents/BOSCO%20CONSULT/BOQ%20AUTO/tender)

## Streamlit Apps

Run the staff-facing production app:

```powershell
py -3.11 -m streamlit run app.py
```

Run the private owner/admin app:

```powershell
py -3.11 -m streamlit run admin_app.py
```

Packaged launcher entrypoints are also available for Windows `.exe` builds:

- [launch_production.py](C:/Users/Ronoz/Documents/BOSCO%20CONSULT/BOQ%20AUTO/launch_production.py)
- [launch_admin.py](C:/Users/Ronoz/Documents/BOSCO%20CONSULT/BOQ%20AUTO/launch_admin.py)

Which app to use:

- `app.py` is the production app for colleagues doing day-to-day tender review, workspace management, and pricing
- `admin_app.py` is the private owner/admin app for training, database maintenance, review promotion, and release control

Production app pages:

- Home / Overview
- Workspace / Jobs
- Tender Analysis
- BOQ Pricing
- Tender -> Pricing
- System / Logs

Admin app pages:

- Admin Home
- Workspace / Jobs
- Tender Analysis
- BOQ Pricing
- Tender -> Pricing
- Manual Ingestion
- Database Tools
- Release Management
- Admin / Logs

The production app intentionally does not expose training/database mutation tools such as imports, normalization, deduplication, review promotion, or release controls.

## Cloud API MVP

BOQ AUTO also includes a minimal FastAPI backend for stateless BOQ processing on platforms such as Google Cloud Run.

Cloud API structure:

- [app/main.py](C:/Users/Ronoz/Documents/BOSCO%20CONSULT/BOQ%20AUTO/app/main.py) FastAPI entrypoint
- [app/routes/health.py](C:/Users/Ronoz/Documents/BOSCO%20CONSULT/BOQ%20AUTO/app/routes/health.py) health check route
- [app/routes/boq.py](C:/Users/Ronoz/Documents/BOSCO%20CONSULT/BOQ%20AUTO/app/routes/boq.py) upload route
- [app/services/file_parser.py](C:/Users/Ronoz/Documents/BOSCO%20CONSULT/BOQ%20AUTO/app/services/file_parser.py) in-memory workbook parsing
- [app/services/cost_engine.py](C:/Users/Ronoz/Documents/BOSCO%20CONSULT/BOQ%20AUTO/app/services/cost_engine.py) in-memory pricing and workbook response generation
- [app/models/boq.py](C:/Users/Ronoz/Documents/BOSCO%20CONSULT/BOQ%20AUTO/app/models/boq.py) API response models

Run locally:

```powershell
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
```

Available endpoints:

- `GET /health`
- `POST /upload-boq`
- `POST /jobs`
- `GET /jobs`
- `GET /jobs/{job_id}`
- `POST /jobs/{job_id}/files`
- `POST /jobs/{job_id}/price-boq`
- `GET /jobs/{job_id}/results`

Example upload:

```powershell
curl -X POST "http://127.0.0.1:8080/upload-boq" `
  -F "file=@boq\sample.xlsx" `
  -F "region=Nairobi" `
  -F "response_format=json"
```

Cloud notes:

- uploads are processed in memory using `BytesIO`
- no persistent local storage is required for request handling
- the API now prices against the existing BOQ AUTO workbook engine and current production database snapshot
- the pricing database defaults to the released production snapshot; override it with `BOQ_AUTO_API_DB_PATH` if needed
- if `BOQ_AUTO_GCS_BUCKET` is set, uploaded inputs, processed workbooks, and audit JSON can be persisted to Google Cloud Storage and returned as `gs://` URIs in the API response
- for a harder production setup, set `BOQ_AUTO_API_DB_GCS_URI` so the service loads the pricing workbook from GCS instead of relying on a database baked into the image
- if you use the SQLite sidecar too, set `BOQ_AUTO_API_DB_SIDECAR_GCS_URI` alongside the workbook URI
- Cloud Run instances cache the downloaded runtime database under `/tmp/boq_auto_runtime_db` and can be forced to refresh it with `BOQ_AUTO_API_DB_REFRESH=true`
- the service is designed to be extended with Google Cloud Storage and Firestore/PostgreSQL without changing the API shape

Cloud Run deployment files:

- [cloudbuild.yaml](C:/Users/Ronoz/Documents/BOSCO%20CONSULT/BOQ%20AUTO/cloudbuild.yaml)
- [scripts/deploy_cloud_run.ps1](C:/Users/Ronoz/Documents/BOSCO%20CONSULT/BOQ%20AUTO/scripts/deploy_cloud_run.ps1)

Example Windows deployment:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\deploy_cloud_run.ps1 `
  -ProjectId "your-gcp-project-id" `
  -Region "us-central1" `
  -ServiceName "boq-auto-api" `
  -BucketName "your-boq-auto-bucket"
```

## Web Platform Slice

The repo now also includes the first internal-first web platform slice:

- [app/db.py](C:/Users/Ronoz/Documents/BOSCO%20CONSULT/BOQ%20AUTO/app/db.py) SQLAlchemy database setup
- [app/orm_models.py](C:/Users/Ronoz/Documents/BOSCO%20CONSULT/BOQ%20AUTO/app/orm_models.py) core Phase 1 tables for jobs, files, and pricing runs
- [app/routes/jobs.py](C:/Users/Ronoz/Documents/BOSCO%20CONSULT/BOQ%20AUTO/app/routes/jobs.py) job workflow API
- [web](C:/Users/Ronoz/Documents/BOSCO%20CONSULT/BOQ%20AUTO/web) Next.js frontend shell

Current scope of this slice:

- create a job with title and region
- upload a BOQ against that job
- price the uploaded BOQ through the existing pricing engine
- persist job metadata, file metadata, and pricing run metadata
- return the latest pricing results through the job API

## Windows Packaging

BOQ AUTO can be deployed on Windows with:

- packaged launcher executables for day-to-day use
- an installer that places the production and admin launchers on the machine

Recommended deployment shape:

- build `BOQ AUTO.exe` for the staff-facing production app
- build `BOQ AUTO Admin.exe` for the private admin app
- install both through a Windows installer so users get desktop/start-menu shortcuts

Packaging files included in the repo:

- [src/launcher.py](C:/Users/Ronoz/Documents/BOSCO%20CONSULT/BOQ%20AUTO/src/launcher.py) shared Streamlit launcher helper
- [launch_production.py](C:/Users/Ronoz/Documents/BOSCO%20CONSULT/BOQ%20AUTO/launch_production.py) packaged production launcher entrypoint
- [launch_admin.py](C:/Users/Ronoz/Documents/BOSCO%20CONSULT/BOQ%20AUTO/launch_admin.py) packaged admin launcher entrypoint
- [packaging/boq_auto_production.spec](C:/Users/Ronoz/Documents/BOSCO%20CONSULT/BOQ%20AUTO/packaging/boq_auto_production.spec) PyInstaller spec for the production launcher
- [packaging/boq_auto_admin.spec](C:/Users/Ronoz/Documents/BOSCO%20CONSULT/BOQ%20AUTO/packaging/boq_auto_admin.spec) PyInstaller spec for the admin launcher
- [packaging/boq_auto_installer.iss](C:/Users/Ronoz/Documents/BOSCO%20CONSULT/BOQ%20AUTO/packaging/boq_auto_installer.iss) Inno Setup installer skeleton
- [scripts/build_windows_dist.ps1](C:/Users/Ronoz/Documents/BOSCO%20CONSULT/BOQ%20AUTO/scripts/build_windows_dist.ps1) helper build script

Build the packaged launchers:

```powershell
python -m pip install -r requirements.txt
powershell -ExecutionPolicy Bypass -File scripts\build_windows_dist.ps1
```

This produces PyInstaller folder-style distributions under:

```text
dist\BOQ AUTO Production\
dist\BOQ AUTO Admin\
```

If you use Inno Setup, point it at [packaging/boq_auto_installer.iss](C:/Users/Ronoz/Documents/BOSCO%20CONSULT/BOQ%20AUTO/packaging/boq_auto_installer.iss) after the PyInstaller build completes.

Important deployment notes:

- Tesseract OCR is still an external runtime dependency unless you decide to package/install it separately
- `OPENAI_API_KEY` should still be provided through the environment on admin machines if AI is enabled
- writable operational data such as logs, outputs, and workspace jobs should remain outside the frozen application logic where possible

## Database Release Workflow

The production app prices against a released database snapshot instead of the live training/master workbook.

Configured release paths live in [config/default.yaml](C:/Users/Ronoz/Documents/BOSCO%20CONSULT/BOQ%20AUTO/config/default.yaml):

- `database_release.master_database_path`
- `database_release.release_dir`
- `database_release.production_database_path`
- `database_release.current_pointer_path`
- `database_release.metadata_path`

Typical release flow:

1. Use `admin_app.py`
2. Update and review the master/training database
3. Open `Release Management`
4. Create a new production release snapshot
5. The snapshot is saved under `database/releases/` with a timestamped versioned name
6. The current production pointer is updated without overwriting older snapshots
7. The staff production app automatically uses the current released snapshot

Release behavior:

- creating a release copies the configured master database into `database/releases/`
- older releases are kept; release creation does not silently overwrite prior snapshots
- release metadata records who created the release and when
- the admin app can reselect an earlier release later for rollback or comparison

## Architecture Upgrade

BOQ AUTO now keeps the existing Excel workflow for compatibility while adding a normalized cost-data sidecar schema for admin/training operations.

Normalized schema:

- `items`
- `sources`
- `aliases`
- `ingestion_logs`
- `item_embeddings`

Practical behavior:

- admin ingestion writes reviewed items into the existing Excel master database and into a SQLite sidecar schema
- production pricing still reads the released Excel snapshot, so existing CLI and workbook outputs remain intact
- when a release snapshot is created, the matching SQLite sidecar is copied alongside the Excel release if present

Matching modes:

- `rule` keeps the existing fuzzy/rule-based behavior and remains the default
- `hybrid` uses a weighted score across semantic similarity, alias hits, unit similarity, and keyword overlap
- `ai` relies on embeddings and falls back safely when no provider/API key is available
- the learning loop is rule-based and database-driven; accepted, rejected, and corrected matches can bias future matching without model retraining

Configuration and AI safety:

- BOQ AUTO loads configuration in layers: `config/default.yaml`, optional `config/local.yaml`, then environment variables with the `BOQ_AUTO_` prefix
- `config/local.yaml` is intended for machine-local overrides and should not be committed
- API keys are not stored in repo config; `OPENAI_API_KEY` must be provided through the environment if AI is enabled
- when `ai.enabled` is `false`, the system stays fully operational in rule mode
- when AI is enabled but embeddings are unavailable, matching falls back safely instead of failing
- the admin UI can update non-secret AI settings in `config/local.yaml`, but it never writes API keys

Admin controls:

- `Manual Ingestion` in the admin app handles reviewed PDF ingestion into the master database
- `Admin AI Control` lets the owner/admin enable or disable AI, switch matching mode, test AI safely, and manage embeddings without affecting production snapshots
- structured ingestion now keeps trade/category, material, unit, and keywords in the normalized schema
- optional admin-only AI assistance can suggest aliases and categories during ingestion
- admin users can generate embeddings for the normalized schema database
- embeddings are generated from `trade | material | description | unit`
- admin users can review ingestion logs from the schema sidecar
- admin users can log match feedback for future tuning from pricing UI previews
- `Manual Ingestion` also shows learning insights such as top corrected queries, most rejected items, and most accepted items, with optional feedback export/clear actions

## Workspace Jobs

The Streamlit UI now supports persistent workspace jobs so colleagues do not need to keep downloading and re-uploading the same tender, BOQ, and output files between steps.

Each job is stored under:

```text
workspace/jobs/<job_id>/
```

Each job folder contains:

- `inputs/` for saved tender, BOQ, and database files
- `intermediate/` for handoff-style working files
- `outputs/` for workbooks, JSON files, CSVs, and other generated artifacts
- `logs/` for lightweight per-job logs
- `state.json` for job metadata, operator attribution, step statuses, artifact versions/history, and action history

Typical flow:

1. Open `Workspace / Jobs`
2. Create a job once with title and region
3. Upload or copy in the tender and optional BOQ once; in the production app pricing uses the current released database automatically
4. Run `Analyze Tender`, `Generate Draft BOQ`, `Run Gap Check`, `Run Tender -> Pricing`, or `Price BOQ Only`
5. Reopen the same job later from disk and continue without re-uploading

Workspace hardening:

- reruns do not overwrite prior important outputs; a new versioned artifact is written and the latest pointer is updated
- each major step tracks `not_started`, `running`, `completed`, or `failed` status in `state.json`
- the current operator/display name is stored with job changes and action history for lightweight attribution
- jobs can be archived to hide them from the default list without deleting their files
- jobs can also be deleted permanently with confirmation from the workspace page

Rerun behavior:

- running a step again writes a new artifact version with revision/timestamp naming
- previous versions remain downloadable from the job artifact history
- the latest successful artifact is shown as the current file for that artifact type

Resume behavior:

- reopening a job restores saved tender, BOQ, and database paths from `state.json`
- the workspace page shows current step status and latest successful artifacts
- colleagues can continue from the next logical step without re-uploading

Production vs admin workspace behavior:

- in the production app, pricing actions resolve the current released production database automatically
- in the admin app, jobs can still point at the master/training database or another working database when needed
- both apps reuse the same workspace/job folders, state tracking, artifact history, and operator attribution

Operator attribution:

- the workspace page allows a simple operator/display name for the current session
- job changes, step runs, artifact writes, and archive/delete actions record operator attribution in job state and logs
- release creation and current-release reselection record operator attribution in release metadata

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

Run Tender Analysis v1 on the demo tender text:

```powershell
py -3.11 -m src.main analyze-tender --input tender\demo_tender_notice.txt --out output\tender_analysis_demo.xlsx --json output\tender_analysis_demo.json
```

The same commands also accept PDF tender files, including scanned PDFs that need OCR fallback:

```powershell
py -3.11 -m src.main analyze-tender --input tender\my_tender.pdf --out output\my_tender_analysis.xlsx
```

Generate the checklist-focused tender workbook:

```powershell
py -3.11 -m src.main tender-checklist --input tender\demo_tender_notice.txt --out output\tender_checklist_demo.xlsx
```

Generate a draft BOQ suggestion workbook from tender text:

```powershell
py -3.11 -m src.main draft-boq --input tender\demo_tender_scope_only.txt --out output\draft_boq_demo.xlsx --json output\draft_boq_demo.json
```

Run a tender-vs-BOQ gap check:

```powershell
py -3.11 -m src.main gap-check --input tender\demo_tender_notice.txt --boq boq\demo_boq.xlsx --out output\gap_check_demo.xlsx --json output\gap_check_demo.json
```

Run the integrated tender-to-pricing workflow:

```powershell
py -3.11 -m src.main tender-price --input tender\demo_tender_notice.txt --db database\qs_database.xlsx --boq boq\demo_boq.xlsx --out output\tender_priced_demo.xlsx --apply --region Nyanza --threshold 78 --json output\tender_priced_demo.json
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

## Tender Analysis

Tender Analysis v1 is for early tender review before BOQ gap checking and pricing. It reads local tender text, PDF, or structured offline extracts, extracts likely requirements, builds a submission checklist, parses likely scope sections, and writes a review-first workbook with:

- `Tender Analysis Summary`
- `Tender Checklist`
- `Scope Summary`
- `Extracted Requirements`

Run the demo input:

```powershell
py -3.11 -m src.main analyze-tender --input tender\demo_tender_notice.txt --out output\tender_analysis_demo.xlsx --json output\tender_analysis_demo.json
```

Run against a normalized extracted tender text file:

```powershell
py -3.11 -m src.main analyze-tender --input tender\my_tender_text.txt --out output\my_tender_analysis.xlsx
```

Run directly against a tender PDF:

```powershell
py -3.11 -m src.main analyze-tender --input tender\my_tender.pdf --out output\my_tender_analysis.xlsx
```

Run against a structured CSV or Excel-derived text export:

```powershell
py -3.11 -m src.main analyze-tender --input tender\my_tender_schedule.xlsx --out output\my_tender_schedule_analysis.xlsx
```

Checklist-focused command path:

```powershell
py -3.11 -m src.main tender-checklist --input tender\demo_tender_notice.txt --out output\tender_checklist_demo.xlsx
```

## Tender Analysis v2

Tender Analysis v2 extends the same workflow with:

- `BOQ Gap Report`
- `Draft BOQ Suggestions`
- `Clarification Log`

Generate draft BOQ suggestions without fabricating quantities:

```powershell
py -3.11 -m src.main draft-boq --input tender\demo_tender_scope_only.txt --out output\draft_boq_demo.xlsx --json output\draft_boq_demo.json
```

Draft BOQ Suggestions are synthesized from tender/specification wording into concise BOQ-style review items. Headings, definitions, references, and weak instruction-only text are filtered where possible, and related clause fragments are merged before suggestion drafting.

Compare tender scope against a BOQ workbook:

```powershell
py -3.11 -m src.main gap-check --input tender\demo_tender_notice.txt --boq boq\demo_boq.xlsx --out output\gap_check_demo.xlsx --json output\gap_check_demo.json
```

Run a review-only gap check when no BOQ has been issued yet:

```powershell
py -3.11 -m src.main gap-check --input tender\demo_tender_scope_only.txt --out output\gap_check_review_only.xlsx
```

## Tender To Pricing

The integrated `tender-price` workflow reuses the existing tender-analysis modules and the existing pricing engine in one review-first path. It:

- analyzes the tender
- runs BOQ gap checking
- generates draft BOQ suggestions
- builds a `Pricing Handoff`
- prices either the supplied BOQ or the tender-only handoff workbook
- writes one integrated workbook with tender review sheets plus pricing/commercial output sheets

Tender only:

```powershell
py -3.11 -m src.main tender-price --input tender\demo_tender_scope_only.txt --db database\qs_database.xlsx --out output\tender_only_priced.xlsx --region Nyanza --threshold 78 --json output\tender_only_priced.json
```

Tender plus BOQ:

```powershell
py -3.11 -m src.main tender-price --input tender\demo_tender_notice.txt --db database\qs_database.xlsx --boq boq\demo_boq.xlsx --out output\tender_priced_demo.xlsx --apply --region Nyanza --threshold 78 --json output\tender_priced_demo.json
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

Tender analysis tests:

```powershell
py -3.11 -m pytest tests\test_tender_analysis.py
```

Tender-to-price tests:

```powershell
py -3.11 -m pytest tests\test_tender_to_price.py
```

UI helper smoke tests:

```powershell
py -3.11 -m pytest tests\test_ui_helpers.py
```

PDF ingestion tests:

```powershell
py -3.11 -m pytest tests\test_pdf_ingestion.py
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
- Tender Analysis is review-first. Low-confidence extractions and ambiguous instructions should still be checked by the estimator or QS before hand-off into BOQ gap review and pricing.
- PDF support is also review-first. OCR output can miss tables, misread quantities, or distort formatting, so extracted tender text should still be checked before pricing decisions are made.
- Draft BOQ generation does not fabricate quantities. It creates synthesized, sectioned, review-first item suggestions with source basis, source excerpts, cautious unit inference, and confidence for QS review.
- The integrated `tender-price` flow also keeps tender-drafted rows and gap-derived rows explicitly flagged in `Pricing Handoff`; missing measurements remain for human review.
- The Streamlit app is a thin internal UI over the same backend modules. Ad hoc runs still use isolated working folders under `output/ui_runs`, while persistent job workspaces are stored under `workspace/jobs`.

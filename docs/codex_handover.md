# Codex Handover

## Purpose

BOQ AUTO is a review-first construction estimating platform built around Kenyan QS workflows.

The product goal is not only to price BOQs, but to do so in a way that:

- preserves estimator trust
- makes uncertain results visible instead of hiding them
- captures reviewer knowledge for future reuse
- grows from a pricing tool into a broader tender and estimating operations platform

The repo currently contains three connected product surfaces over the same core engine:

- local/desktop workflows in `src/`
- Streamlit production/admin apps in `app.py` and `admin_app.py`
- cloud/web platform workflows in `app/` and `web/`

## Product Intent

The intended long-term workflow is:

1. maintain and improve a controlled commercial knowledge base
2. price BOQs and tender-derived handoff items through a cautious engine
3. expose uncertain matches in a review-first queue
4. let estimator decisions improve aliases, live rates, and future matching behavior

This repository should not drift into disconnected pipelines. New work should extend the current engine, review flow, and release model rather than bypassing them.

## Phase Map

### Phase 1

Platform foundation.

- BOQ pricing engine
- Excel workbook read/write flow
- audit JSON and unmatched export
- FastAPI backend
- Cloud Run deployment path
- job workflow: create job, upload BOQ, run pricing
- Cloud SQL/GCS-backed platform data path
- Next.js hosted frontend
- Firebase-authenticated protected platform routes
- `GET /price-check`
- `GET /knowledge/candidates`

### Phase 1.5

Stabilization and hardening.

- Firebase Auth enforcement on protected API routes
- hosted frontend auth configuration
- CORS for hosted frontend to API
- workspace failure handling instead of generic hosted crashes
- malformed workbook compatibility handling
- review-first match diagnostics through engine, API, and UI

### Phase 2

Pricing quality and review maturity.

- reduce false positives
- harden category-aware matching
- improve section/category hints for weak item families
- make review queue and workspace explain weak output clearly
- prefer honest `review` / `unmatched` over misleading confident matches

This is the current active product phase.

### Phase 3

Learning-loop completion.

- reviewer action workflows in the hosted platform
- promotion of approved knowledge into aliases/rate library/candidate stores
- tighter use of feedback in matching
- likely lightweight role-ready authorization

### Phase 4

Full tender intelligence platform.

- tender analysis
- draft BOQ generation
- BOQ gap checking
- tender-to-pricing workflows
- broader internal estimating workspace operations

The foundations for this phase already exist in `src/`, but the hosted platform has not yet absorbed all of them.

## Current Architecture

### Core engine

- `src/engine.py`
  Orchestrates workbook pricing, matching, build-up fallback, audit output, and quotation results.
- `src/matcher.py`
  Performs line-to-library decisioning using text, section, unit, alias, and now review-first diagnostics.
- `src/matching_engine.py`
  Supports `rule`, `ai`, and `hybrid` ranking paths.
- `src/learning_engine.py`
  Applies reviewer feedback adjustments from the normalized sidecar schema.
- `src/section_inference.py`
  Infers likely sections from sheet names, headings, and rule triggers.
- `src/workbook_writer.py`
  Writes Match Suggestions, Quotation Summary, Commercial Review, and related review-first sheets.

### Cloud/web platform

- `app/main.py`
  FastAPI entrypoint and middleware setup.
- `app/routes/jobs.py`
  Protected job workflow API.
- `app/routes/insights.py`
  Protected review/price evidence API.
- `app/auth.py`
  Firebase bearer-token verification for protected routes.
- `app/services/cost_engine.py`
  Cloud-native wrapper over the core pricing engine.
- `app/services/jobs.py`
  Job orchestration and run/result persistence.
- `app/services/insights.py`
  Review-first evidence extraction from recent job results.
- `app/routes/review_tasks.py`
  Protected reviewer-task API for syncing weak rows into claimable review work.
- `app/services/review_tasks.py`
  Task generation, claiming, and submission logic for the hosted reviewer workflow.
- `web/`
  Next.js hosted frontend for login, jobs, price checker, knowledge review, and reviewer tasks.

### Review and learning foundations

- `CandidateMatches`
- `Candidate Review`
- `ReviewLog`
- normalized sidecar schema and `match_feedback`
- admin/CLI review merge and promotion commands

These already exist and should be reused, not replaced.

## Live/Operational Status

As of the latest tracked state in this repo:

- protected backend routes require Firebase bearer tokens
- hosted frontend is configured for Firebase Auth and App Hosting
- cloud job workflow is implemented
- workbook parsing and pricing flow are working
- malformed workbook metadata handling was added
- match diagnostics now flow through engine, audit, API, and UI
- reviewer task queue MVP now exists in the hosted platform:
  - weak job rows can be synced into review tasks
  - reviewers can claim tasks
  - reviewers can submit structured review responses
  - the queue supports shared scope and "my tasks only" scope
  - backend guardrails prevent one reviewer from submitting another reviewer's claimed task
  - submitted tasks can now move into QA states: `approved`, `rejected`, or `escalated`
- the first taxonomy-compatible schema slice has started in `src/cost_schema.py`:
  - normalized items now support `domain`, `work_family`, `item_kind`, and `project_context`
  - these fields are inferred from current item descriptions / categories so the schema can evolve without breaking the Excel rate library flow
- the current in-flight reviewer slice extends tasks toward learning-loop hooks:
  - QA outcomes now map to `promotion_target` / `promotion_status`
  - approved reviewer confirmations can feed match-feedback logging when a canonical item code exists
  - the hosted reviewer inbox now exposes promotion readiness and learning-hook status directly
- approved reviewer outcomes can now create durable normalized-schema records:
  - manual-rate approvals can persist `rate_observations`
  - no-good-match / escalation style outcomes can persist `candidate_review_records`
  - confirmed alternate phrasing can persist `alias_suggestions`
- the immediate bridge priority is to sync those normalized reviewer artifacts back into workbook-era `CandidateMatches`
  - the workbook review and promotion commands should remain the canonical promotion path
  - normalized reviewer artifacts should feed that path, not replace it
  - the intended operator flow is:
    1. reviewer task is approved in the hosted platform
    2. normalized artifact is written to the SQLite sidecar
    3. a sync step materializes it into `CandidateMatches`
    4. existing `review-report`, `merge-reviewed`, and `promote-approved` commands continue from there
- that bridge now exists:
  - `sync-review-artifacts` was added to the CLI
  - approved `rate_observations` sync in as already-approved `ratelibrary` promotion rows
  - approved `alias_suggestions` sync in as already-approved `aliases` promotion rows
  - `candidate_review_records` sync in as pending `candidatematches` rows for further workbook review
  - dedupe is driven by `schema-task:<task_id>` markers in `CandidateMatches.source_file`
- review tasks now support a first task-type framework:
  - each task carries `task_type`
  - each task carries an engine-generated `task_question`
  - each task carries a lightweight `response_schema` so the reviewer knows the expected answer shape
  - weak rows can now be framed as concrete reviewer prompts such as manual-rate entry, candidate selection, or category/section checks
- the web UI now uses a darker operations-style theme so the hosted platform feels more deliberate and less prototype-like
- the immediate next slice is to turn weak rows into typed reviewer questions:
  - each review task should carry a `task_type`
  - the engine should generate a concrete reviewer question instead of a generic review request
  - reviewer tasks should describe the expected response shape so the future marketplace flow can scale

Recent important commits:

- `4550f0e` Add reviewer task queue MVP
- `219bf9f` Add review-first match diagnostics across API and UI
- `8e47fd7` Harden Excel workbook loading for malformed metadata
- `2e70630` Allow hosted frontend CORS on protected API routes
- `d91fb78` Harden web workspace and enforce Firebase API auth
- `6a92572` Fix hosted Firebase Auth configuration
- repo deployment helper now exists at `scripts/deploy_all_cloudshell.sh` for one-command Cloud Shell milestone deploys

Recent uncommitted work in the current checkpoint:

- normalized reviewer artifacts now bridge back into workbook-era promotion flow via:
  - `python -m src.main sync-review-artifacts --db <workbook.xlsx>`
  - optional `--schema <path.sqlite>`
  - optional `--refresh-review-report`
- this keeps the review loop unified:
  - hosted reviewer task approval writes normalized artifacts
  - `sync-review-artifacts` materializes them into `CandidateMatches`
  - existing workbook review/promotion commands can continue from there
- that follow-up hosted bridge slice now exists:
  - `GET /review-tasks/bridge` returns normalized artifact counts plus synced workbook bridge counts
  - `POST /review-tasks/bridge/sync` runs the sync into `CandidateMatches` and refreshes `Candidate Review`
  - the hosted reviewer page now shows the bridge summary and a sync action
  - this makes the reviewer-learning bridge visible in the web workflow instead of CLI-only
- the next runtime alignment fix is to make that hosted bridge reuse the same cloud database resolution as pricing:
  - pricing already supports `BOQ_AUTO_API_DB_GCS_URI`
  - the bridge must follow that same runtime workbook path instead of only local release paths
  - `scripts/deploy_all_cloudshell.sh` should also set `BOQ_AUTO_API_DB_SIDECAR_GCS_URI` by default so Cloud Run has the normalized schema alongside the workbook
- the latest product diagnosis from live price-check evidence is broader than any one keyword like `survey`:
  - review-first guardrails are doing their job and downgrading absurd specialist rows to `review` / `unmatched`
  - however, the insights UI still exposes the raw fallback candidate text even when that candidate is obviously nonsense
  - the core gap is therefore:
    1. under-modeled specialist domains and work families
    2. thin specialist candidate coverage
    3. bad fallback display in review-facing UI even when the engine is correctly uncertain
  - the immediate next slice should suppress obviously absurd fallback matches from the hosted insights views while preserving the raw `matched_description` for audit/debug paths
  - after that, the stronger long-term fix remains taxonomy-first knowledge growth for specialist domains rather than matcher-only tuning
- focused verification status for this checkpoint:
  - direct runtime smoke check passed for sync, dedupe, and promotion behavior
  - local pytest remains partially blocked in this environment by Windows temp-directory permissions, so the smoke check was used to verify bridge behavior before commit
  - the hosted bridge API slice was verified with:
    - a direct FastAPI `TestClient` smoke script covering `/review-tasks/bridge` and `/review-tasks/bridge/sync`
    - successful `npm run build` in `web/`
    - successful `py_compile` of the touched backend Python modules

## Deployment Rules

This distinction matters:

- `git pull` in Cloud Shell only updates source code in the Cloud Shell checkout
- backend changes become live only after:
  - `gcloud builds submit ...`
  - `gcloud run deploy ...`
- frontend changes become live only after:
  - `firebase deploy --only apphosting`

Pulling alone does not update the live frontend or backend.

### Standard Cloud Shell milestone deploy

Use the repo helper:

- default Cloud Shell redeploy sequence:

```bash
cd ~/boq-auto
git pull
bash scripts/deploy_all_cloudshell.sh
```

That single command:

- pulls latest source
- builds the backend image
- deploys Cloud Run with the expected env vars / secret wiring
- deploys Firebase App Hosting
- runs quick backend health/auth checks

Useful toggles:

- `DEPLOY_FRONTEND=false bash scripts/deploy_all_cloudshell.sh`
- `DEPLOY_BACKEND=false bash scripts/deploy_all_cloudshell.sh`
- `RUN_CHECKS=false bash scripts/deploy_all_cloudshell.sh`

### Backend runtime assumptions

Protected platform routes depend on:

- `BOQ_AUTO_FIREBASE_AUTH_ENABLED=true`
- `BOQ_AUTO_FIREBASE_PROJECT_ID=<project-id>`

Cloud SQL-backed web platform/API deployment depends on:

- `BOQ_AUTO_CLOUD_SQL_CONNECTION_NAME`
- `BOQ_AUTO_DB_NAME`
- `BOQ_AUTO_DB_USER`
- `BOQ_AUTO_DB_PASSWORD` or Secret Manager mount

### Frontend runtime assumptions

`web/apphosting.yaml` must expose:

- `BOQ_AUTO_API_BASE_URL`
- `NEXT_PUBLIC_BOQ_AUTO_API_BASE_URL`
- `NEXT_PUBLIC_FIREBASE_API_KEY`
- `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN`
- `NEXT_PUBLIC_FIREBASE_PROJECT_ID`
- `NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET`
- `NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID`
- `NEXT_PUBLIC_FIREBASE_APP_ID`

### Runtime database note

- pricing and the hosted reviewer bridge should resolve the same runtime workbook/schema pair
- in Cloud Run, that usually means setting both:
  - `BOQ_AUTO_API_DB_GCS_URI`
  - `BOQ_AUTO_API_DB_SIDECAR_GCS_URI`
- if the workbook URI is set but the sidecar URI is missing, pricing can still work while the hosted learning bridge reports unavailable

## Current Priorities

Immediate checkpoint rule for future Codex instances:

- update this handover file before substantial new work whenever a token or capacity cutoff feels possible
- prefer coherent checkpoints with verification over large half-finished diffs
- preserve the user's preference for intermittent commits/pushes and a handover that is current enough for direct takeover

### Research-backed architecture note

There is now a strong repo-grounded case for a taxonomy-first knowledge model.

Why:

- actual BOQs in the repo already span domains like preliminaries, dayworks plant, earthworks, excavation, road furniture, elevated approach lighting, survey equipment, laboratory equipment, and engineer accommodation
- the current rate library is still much narrower and is dominated by Earthworks / Dayworks / Concrete
- current normalized schema fields (`category`, `subcategory`, `material`, `keywords`) are useful but too flat for the range of project types already visible

See:

- `docs/taxonomy_strategy.md`

This means the next major knowledge-layer improvement should not be only matcher tuning. It should be:

1. define a canonical construction taxonomy
2. map current items and aliases into it
3. treat price observations as data attached to canonical items, not as the only source of structure
4. let future reviewer promotions feed canonical items / aliases / observations cleanly

### Immediate product priority

Improve pricing quality, especially for weak/non-core categories:

- furniture/accommodation items
- survey items
- laboratory/testing items
- electrical support items
- generic placeholder matches such as preliminaries/general items/generic concrete

### What “better” means

- fewer obviously wrong confident matches
- more honest `review` and `unmatched` decisions
- stronger explanation of why an item is weak
- a more useful review queue for curating future knowledge

### Current next-phase direction

1. strengthen category-aware and section-aware match guardrails
2. improve review queue usefulness and triage UX
3. identify top missing knowledge clusters from real bad runs
4. extend hosted reviewer action workflows so submitted tasks can feed promotions and learning
5. begin taxonomy-first schema design for domains such as roads, structures, water/pipes, plant, survey, lab/testing, and accommodation/furniture

### Immediate reviewer-workflow follow-up

The current reviewer queue is intentionally MVP-level. The next best extensions are:

- bulk actions for grouped weak items
- deeper promotion hooks from submitted review tasks into the existing review/promotion foundations
- reviewer performance and workload summaries
- clearer mapping between submitted task outcomes and `match_feedback` / promotion flows
- richer task-type generation so more uncertainty modes become explicit reviewer questions instead of generic review prompts

### Current in-flight direction

The next active slice after this handover update is:

1. connect the new normalized reviewer artifacts back into the workbook-era review/promotion foundations cleanly
2. keep the taxonomy slice backward-compatible with the current rate library and Excel flow
3. preserve the review-first architecture without creating a separate moderation pipeline
4. keep the darker hosted UI direction consistent across new pages and states
5. deepen task-type-driven reviewer questions so the engine can ask reviewers exactly what kind of decision is needed
6. keep using `docs/codex_handover.md` as a checkpoint file whenever work is paused or handed over
7. keep `scripts/deploy_all_cloudshell.sh` updated whenever runtime env vars or deploy assumptions change

## Working Principles For The Next Codex

- modify existing modules in place
- do not create disconnected alternate pipelines
- keep the engine review-first
- prefer conservative decisions over misleading matches
- reuse config, logging, models, and workbook output patterns
- preserve CLI and admin flow coherence
- keep web, API, and engine payloads aligned

When improving quality, prefer extending these current seams:

- `MatchResult` for diagnostics
- audit JSON for engine truth
- insights service for review-friendly API payloads
- hosted web pages for human triage

## Known Constraints And Notes

- `database/master/` is intentionally untracked and should not be committed casually
- the normalized schema/feedback path exists, but hosted reviewer actions are not yet complete
- some local Windows test runs may need explicit temp/cache handling under sandboxed environments
- current taxonomy-slice verification status:
  - taxonomy inference test passes: `tests/test_cost_schema.py::test_taxonomy_fields_are_inferred_for_equipment_and_utilities`
  - full `tests/test_cost_schema.py tests/test_manual_ingestion_pipeline.py` coverage is partially blocked by Windows temp-directory permission issues in this environment, not by an observed schema logic failure
- tender analysis and tender-to-pricing foundations are already substantial, but the hosted product has not fully absorbed them

## Recommended Next Work Slice

If handing over right now, the best immediate task is:

1. connect the new normalized reviewer artifacts (`rate_observations`, `candidate_review_records`, `alias_suggestions`) back into the workbook-era review/promotion foundations cleanly
2. define the next canonical BOQ AUTO taxonomy slice beyond the initial inferred fields
3. extend the schema so current flat items can map into domain / family / category / canonical item structure more explicitly
4. keep matcher and reviewer UX aligned with that taxonomy, the darker hosted UI direction, and the new task-type question model
5. only then continue deeper matcher tuning against the improved knowledge structure

That continues the current product direction without wasting the architecture already built.

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

Recent important commits:

- `4550f0e` Add reviewer task queue MVP
- `219bf9f` Add review-first match diagnostics across API and UI
- `8e47fd7` Harden Excel workbook loading for malformed metadata
- `2e70630` Allow hosted frontend CORS on protected API routes
- `d91fb78` Harden web workspace and enforce Firebase API auth
- `6a92572` Fix hosted Firebase Auth configuration

## Deployment Rules

This distinction matters:

- `git pull` in Cloud Shell only updates source code in the Cloud Shell checkout
- backend changes become live only after:
  - `gcloud builds submit ...`
  - `gcloud run deploy ...`
- frontend changes become live only after:
  - `firebase deploy --only apphosting`

Pulling alone does not update the live frontend or backend.

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

## Current Priorities

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

### Immediate reviewer-workflow follow-up

The current reviewer queue is intentionally MVP-level. The next best extensions are:

- bulk actions for grouped weak items
- promotion hooks from submitted review tasks into the existing review/promotion foundations
- reviewer performance and workload summaries
- clearer mapping between submitted task outcomes and `match_feedback` / promotion flows

### Current in-flight direction

The next active slice after this handover update is:

1. connect approved/escalated review tasks to promotion and feedback hooks
2. add bulk actions for grouped reviewer work
3. preserve the review-first architecture without creating a separate moderation pipeline
4. keep using `docs/codex_handover.md` as a checkpoint file whenever work is paused or handed over

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
- tender analysis and tender-to-pricing foundations are already substantial, but the hosted product has not fully absorbed them

## Recommended Next Work Slice

If handing over right now, the best immediate task is:

1. inspect the latest poor pricing runs
2. classify dominant bad-match patterns
3. harden matcher/category/section guardrails
4. make knowledge review/workspace triage clearer
5. prepare for reviewer action and promotion workflows

That continues the current product direction without wasting the architecture already built.

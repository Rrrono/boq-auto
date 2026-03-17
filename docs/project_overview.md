# Project Overview

## Purpose

BOQ AUTO is a local estimating and quotations platform for Excel BOQs and Excel rate libraries in Kenyan QS workflows.

It is designed around three practical stages:

1. Build and maintain the database
2. Price BOQs and prepare commercial quotations
3. Review uncertain results and learn from estimator decisions

## Main Module Boundaries

- `src/engine.py`
  Orchestrates database loading, workbook pricing, matching, build-up fallback, and quotation output generation.
- `src/workbook_reader.py`
  Detects workable BOQ structures from messy Excel sheets.
- `src/matcher.py`
  Performs direct matching with section, alias, unit, and region awareness.
- `src/buildup.py`
  Handles build-up fallback pricing when direct library matching is weak.
- `src/workbook_writer.py`
  Writes priced BOQs and review/commercial sheets back to Excel.
- `src/commercial.py`
  Applies markups, VAT, regional factors, and quotation summary calculations.
- `src/ingestion.py`
  Owns structured imports, duplicate handling, review queues, promotion, and learning exports.

## Working Style

- Keep the Excel database as the live operational store.
- Use `CandidateMatches` and `Candidate Review` as controlled review queues.
- Treat `ReviewLog` as the audit trail.
- Treat `Aliases` as estimator-approved language learning.
- Promote only reviewed and commercially sensible records into `RateLibrary`.

## Output Philosophy

- Preserve the source BOQ layout where practical.
- Add reviewable sheets rather than hiding decisions.
- Make client-ready totals visible, but keep internal review signals available for the estimating team.

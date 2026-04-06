"""Insight helpers built from recent job pricing runs."""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.insights import (
    KnowledgeCandidateResponse,
    KnowledgeFocusAreaResponse,
    KnowledgeQueueResponse,
    PriceCheckResponse,
    PriceObservationResponse,
)
from app.orm_models import Job


def _recent_priced_jobs(db: Session, *, limit: int = 8) -> list[Job]:
    jobs = list(db.query(Job).order_by(Job.updated_at.desc()).all())
    return [job for job in jobs if job.runs][:limit]


def _latest_result_payload(job: Job) -> dict | None:
    if not job.runs:
        return None
    latest_run = sorted(job.runs, key=lambda item: item.created_at, reverse=True)[0]
    return json.loads(latest_run.result_payload)


def _item_flag_reasons(item: dict) -> list[str]:
    return [str(value) for value in item.get("flag_reasons", []) if str(value).strip()]


def _focus_area_label(item: KnowledgeCandidateResponse) -> str:
    description = item.description.lower()
    reasons = set(item.flag_reasons)
    if "survey" in description or "theodolite" in description or "level" in description:
        return "Survey knowledge gap"
    if "laboratory" in description or "lab" in description or "sieve" in description or "mould" in description:
        return "Lab and testing items"
    if "chair" in description or "desk" in description or "cupboard" in description or "table" in description:
        return "Furniture and accommodation"
    if "cable" in description or "conduit" in description or "transformer" in description or "lighting" in description:
        return "Electrical support items"
    if "category_mismatch" in reasons:
        return "Category mismatch cleanup"
    if "section_mismatch" in reasons:
        return "Section mapping cleanup"
    if "generic_match" in reasons:
        return "Generic fallback cleanup"
    if item.decision == "unmatched":
        return "Unclassified items"
    return "General review backlog"


def _candidate_priority(item: KnowledgeCandidateResponse) -> tuple[int, float]:
    severity = 0
    if item.decision == "unmatched":
        severity -= 4
    if item.category_mismatch_flag:
        severity -= 3
    if item.generic_match_flag:
        severity -= 2
    if item.section_mismatch_flag:
        severity -= 1
    return severity, item.confidence_score


def search_price_observations(db: Session, query: str = "", *, limit: int = 50) -> PriceCheckResponse:
    normalized_query = query.strip().lower()
    priced_jobs = _recent_priced_jobs(db)
    observations: list[PriceObservationResponse] = []

    for job in priced_jobs:
        payload = _latest_result_payload(job)
        if not payload:
            continue
        for item in payload.get("items", []):
            rate = item.get("rate")
            if not isinstance(rate, (int, float)):
                continue
            description = str(item.get("description", ""))
            matched_description = str(item.get("matched_description", ""))
            haystack = f"{description} {matched_description}".lower()
            if normalized_query and normalized_query not in haystack:
                continue
            observations.append(
                PriceObservationResponse(
                    job_id=job.id,
                    job_title=job.title,
                    region=job.region,
                    description=description,
                    matched_description=matched_description,
                    unit=str(item.get("unit", "")),
                    rate=float(rate),
                    amount=item.get("amount"),
                    decision=str(item.get("decision", "")),
                    confidence_score=float(item.get("confidence_score", 0.0) or 0.0),
                    confidence_band=str(item.get("confidence_band", "very_low") or "very_low"),
                    flag_reasons=_item_flag_reasons(item),
                    generic_match_flag=bool(item.get("generic_match_flag", False)),
                    category_mismatch_flag=bool(item.get("category_mismatch_flag", False)),
                    section_mismatch_flag=bool(item.get("section_mismatch_flag", False)),
                )
            )

    observations = observations[:limit]
    average_rate = None
    if observations:
        average_rate = sum(item.rate for item in observations) / len(observations)

    observed_rows = 0
    for job in priced_jobs:
        payload = _latest_result_payload(job)
        if payload:
            observed_rows += sum(1 for item in payload.get("items", []) if isinstance(item.get("rate"), (int, float)))

    return PriceCheckResponse(
        query=query,
        scanned_jobs=len(priced_jobs),
        observed_rows=observed_rows,
        filtered_rows=len(observations),
        average_rate=average_rate,
        observations=observations,
    )


def build_knowledge_queue(db: Session, *, limit: int = 50) -> KnowledgeQueueResponse:
    priced_jobs = _recent_priced_jobs(db)
    candidates: list[KnowledgeCandidateResponse] = []

    for job in priced_jobs:
        payload = _latest_result_payload(job)
        if not payload:
            continue
        for item in payload.get("items", []):
            decision = str(item.get("decision", ""))
            review_flag = bool(item.get("review_flag", False))
            if not review_flag and decision not in {"review", "unmatched"}:
                continue
            candidates.append(
                KnowledgeCandidateResponse(
                    job_id=job.id,
                    job_title=job.title,
                    region=job.region,
                    description=str(item.get("description", "")),
                    matched_description=str(item.get("matched_description", "")),
                    decision=decision,
                    confidence_score=float(item.get("confidence_score", 0.0) or 0.0),
                    confidence_band=str(item.get("confidence_band", "very_low") or "very_low"),
                    review_flag=review_flag,
                    flag_reasons=_item_flag_reasons(item),
                    generic_match_flag=bool(item.get("generic_match_flag", False)),
                    category_mismatch_flag=bool(item.get("category_mismatch_flag", False)),
                    section_mismatch_flag=bool(item.get("section_mismatch_flag", False)),
                )
            )

    ordered = sorted(candidates, key=_candidate_priority)[:limit]
    unmatched_count = sum(1 for item in candidates if item.decision == "unmatched")
    review_count = sum(1 for item in candidates if item.decision == "review")
    focus_area_counts: dict[str, int] = {}
    for item in candidates:
        label = _focus_area_label(item)
        focus_area_counts[label] = focus_area_counts.get(label, 0) + 1
    focus_areas = [
        KnowledgeFocusAreaResponse(label=label, count=count)
        for label, count in sorted(focus_area_counts.items(), key=lambda entry: (-entry[1], entry[0]))[:5]
    ]

    return KnowledgeQueueResponse(
        scanned_jobs=len(priced_jobs),
        candidate_count=len(candidates),
        unmatched_count=unmatched_count,
        review_count=review_count,
        focus_areas=focus_areas,
        candidates=ordered,
    )

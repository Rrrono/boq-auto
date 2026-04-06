"""Insight helpers built from recent job pricing runs."""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.insights import (
    KnowledgeCandidateResponse,
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

    ordered = sorted(candidates, key=lambda item: item.confidence_score)[:limit]
    unmatched_count = sum(1 for item in candidates if item.decision == "unmatched")
    review_count = sum(1 for item in candidates if item.decision == "review")

    return KnowledgeQueueResponse(
        scanned_jobs=len(priced_jobs),
        candidate_count=len(candidates),
        unmatched_count=unmatched_count,
        review_count=review_count,
        candidates=ordered,
    )

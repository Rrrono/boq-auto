"""Pydantic models for Phase 1 insight endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PriceObservationResponse(BaseModel):
    job_id: str
    job_title: str
    region: str
    description: str
    matched_description: str = ""
    unit: str = ""
    rate: float
    amount: float | None = None
    decision: str = ""
    confidence_score: float = 0.0


class PriceCheckResponse(BaseModel):
    query: str = ""
    scanned_jobs: int = 0
    observed_rows: int = 0
    filtered_rows: int = 0
    average_rate: float | None = None
    observations: list[PriceObservationResponse] = Field(default_factory=list)


class KnowledgeCandidateResponse(BaseModel):
    job_id: str
    job_title: str
    region: str
    description: str
    matched_description: str = ""
    decision: str = ""
    confidence_score: float = 0.0
    review_flag: bool = False


class KnowledgeQueueResponse(BaseModel):
    scanned_jobs: int = 0
    candidate_count: int = 0
    unmatched_count: int = 0
    review_count: int = 0
    candidates: list[KnowledgeCandidateResponse] = Field(default_factory=list)

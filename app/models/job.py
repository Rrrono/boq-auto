"""Pydantic models for job workflows."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.boq import BoqProcessingResponse


class JobCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    region: str = Field(min_length=1, max_length=128)


class JobFileResponse(BaseModel):
    id: int
    file_type: str
    filename: str
    storage_uri: str
    content_type: str
    created_at: datetime


class JobRunResponse(BaseModel):
    id: int
    run_type: str
    status: str
    processed: int
    matched: int
    flagged: int
    total_cost: float
    currency: str
    output_storage_uri: str
    audit_storage_uri: str
    created_at: datetime


class JobResponse(BaseModel):
    id: str
    title: str
    region: str
    status: str
    created_at: datetime
    updated_at: datetime
    files: list[JobFileResponse] = Field(default_factory=list)
    runs: list[JobRunResponse] = Field(default_factory=list)


class JobPricingResponse(BaseModel):
    job: JobResponse
    pricing: BoqProcessingResponse

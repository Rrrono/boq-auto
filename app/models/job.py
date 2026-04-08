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


class ReviewTaskResponse(BaseModel):
    id: int
    job_id: str
    job_run_id: int
    status: str
    source_row_key: str
    sheet_name: str
    row_number: int
    description: str
    matched_description: str
    matched_item_code: str = ""
    task_type: str = "match_confirmation"
    focus_area: str = ""
    specialist_gap_flag: bool = False
    task_question: str = ""
    response_schema: list[str] = Field(default_factory=list)
    unit: str
    decision: str
    confidence_score: float
    confidence_band: str
    flag_reasons: list[str] = Field(default_factory=list)
    reviewer_uid: str = ""
    reviewer_email: str = ""
    submitted_decision: str = ""
    submitted_category_direction: str = ""
    submitted_match_description: str = ""
    submitted_rate: float | None = None
    reviewer_note: str = ""
    qa_status: str = "pending"
    qa_reviewer_uid: str = ""
    qa_reviewer_email: str = ""
    qa_note: str = ""
    promotion_target: str = ""
    promotion_status: str = "pending"
    feedback_action: str = ""
    submitted_at: datetime | None = None
    qa_updated_at: datetime | None = None
    feedback_logged_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ReviewTaskSyncResponse(BaseModel):
    job_id: str
    synced_count: int
    open_count: int
    tasks: list[ReviewTaskResponse] = Field(default_factory=list)


class ReviewTaskBacklogAreaResponse(BaseModel):
    label: str
    count: int = 0


class ReviewTaskReviewerSummaryResponse(BaseModel):
    reviewer_email: str
    claimed_count: int = 0
    submitted_count: int = 0
    approved_count: int = 0
    promotion_logged_count: int = 0


class ReviewTaskPromotionSummaryResponse(BaseModel):
    label: str
    count: int = 0


class ReviewTaskBridgeSummaryResponse(BaseModel):
    available: bool
    workbook_path: str = ""
    schema_path: str = ""
    rate_observations: int = 0
    alias_suggestions: int = 0
    candidate_review_records: int = 0
    synced_candidate_rows: int = 0
    pending_workbook_candidates: int = 0
    taxonomy_backlog: list[ReviewTaskBacklogAreaResponse] = Field(default_factory=list)
    reviewer_workload: list[ReviewTaskReviewerSummaryResponse] = Field(default_factory=list)
    promotion_pipeline: list[ReviewTaskPromotionSummaryResponse] = Field(default_factory=list)


class ReviewTaskBridgeSyncResponse(BaseModel):
    available: bool
    workbook_path: str = ""
    schema_path: str = ""
    synced_count: int = 0
    skipped_duplicates: int = 0
    review_report_rows: int = 0
    bridge: ReviewTaskBridgeSummaryResponse


class ReviewTaskSubmissionRequest(BaseModel):
    decision: str = Field(min_length=1, max_length=32)
    category_direction: str = Field(default="", max_length=128)
    matched_description: str = Field(default="", max_length=2000)
    rate: float | None = None
    reviewer_note: str = Field(default="", max_length=4000)


class ReviewTaskQaRequest(BaseModel):
    qa_status: str = Field(min_length=1, max_length=32)
    qa_note: str = Field(default="", max_length=4000)


class ReviewTaskBulkClaimRequest(BaseModel):
    task_ids: list[int] = Field(default_factory=list, max_length=100)


class ReviewTaskBulkClaimResponse(BaseModel):
    requested_count: int
    claimed_count: int
    skipped_count: int
    tasks: list[ReviewTaskResponse] = Field(default_factory=list)


class ReviewTaskBulkQaRequest(BaseModel):
    task_ids: list[int] = Field(default_factory=list, max_length=100)
    qa_status: str = Field(min_length=1, max_length=32)
    qa_note: str = Field(default="", max_length=4000)


class ReviewTaskBulkQaResponse(BaseModel):
    requested_count: int
    updated_count: int
    skipped_count: int
    tasks: list[ReviewTaskResponse] = Field(default_factory=list)

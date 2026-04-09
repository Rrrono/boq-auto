"""Reviewer task workflow routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import AuthenticatedUser, require_authenticated_user
from app.db import get_db
from app.models.job import (
    ReviewTaskBulkClaimRequest,
    ReviewTaskBulkClaimResponse,
    ReviewTaskBulkPromotionRequest,
    ReviewTaskBulkPromotionResponse,
    ReviewTaskBulkQaRequest,
    ReviewTaskBulkQaResponse,
    ReviewTaskBridgeSummaryResponse,
    ReviewTaskBridgeSyncResponse,
    ReviewTaskQaRequest,
    ReviewTaskResponse,
    ReviewTaskSubmissionRequest,
    ReviewTaskSyncResponse,
)
from app.services.jobs import get_job
from app.services.review_tasks import (
    claim_review_task,
    bulk_claim_review_tasks,
    bulk_close_logged_review_tasks,
    bulk_qa_review_tasks,
    get_review_task_bridge_summary,
    get_review_task,
    list_review_tasks,
    qa_review_task,
    serialize_review_task,
    submit_review_task,
    sync_review_task_bridge,
    sync_review_tasks_for_job,
)


router = APIRouter(tags=["review-tasks"])


@router.get("/review-tasks", response_model=list[ReviewTaskResponse])
def list_review_tasks_endpoint(
    status: str | None = Query(default=None),
    qa_status: str | None = Query(default=None),
    promotion_status: str | None = Query(default=None),
    focus_area: str | None = Query(default=None),
    job_id: str | None = Query(default=None),
    specialist_only: bool = Query(default=False),
    mine: bool = Query(default=False),
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_authenticated_user),
) -> list[ReviewTaskResponse]:
    reviewer_uid = user.uid if mine else None
    tasks = list_review_tasks(db, status=status, reviewer_uid=reviewer_uid, job_id=job_id)
    serialized = [serialize_review_task(task) for task in tasks]
    if qa_status:
        serialized = [task for task in serialized if task.qa_status == qa_status]
    if promotion_status:
        serialized = [task for task in serialized if task.promotion_status == promotion_status]
    if focus_area:
        normalized_focus_area = focus_area.strip().lower().replace(" ", "_")
        serialized = [task for task in serialized if task.focus_area == normalized_focus_area or task.submitted_category_direction == normalized_focus_area]
    if specialist_only:
        serialized = [task for task in serialized if task.specialist_gap_flag]
    return serialized


@router.post("/review-tasks/bulk/claim", response_model=ReviewTaskBulkClaimResponse)
def bulk_claim_review_tasks_endpoint(
    payload: ReviewTaskBulkClaimRequest,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_authenticated_user),
) -> ReviewTaskBulkClaimResponse:
    claimed, skipped_count = bulk_claim_review_tasks(
        db,
        payload.task_ids,
        reviewer_uid=user.uid,
        reviewer_email=user.email,
    )
    return ReviewTaskBulkClaimResponse(
        requested_count=len(payload.task_ids),
        claimed_count=len(claimed),
        skipped_count=skipped_count,
        tasks=[serialize_review_task(task) for task in claimed],
    )


@router.post("/review-tasks/bulk/qa", response_model=ReviewTaskBulkQaResponse)
def bulk_qa_review_tasks_endpoint(
    payload: ReviewTaskBulkQaRequest,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_authenticated_user),
) -> ReviewTaskBulkQaResponse:
    normalized_status = payload.qa_status.strip().lower()
    if normalized_status not in {"approved", "rejected", "escalated"}:
        raise HTTPException(status_code=400, detail="QA status must be approved, rejected, or escalated.")
    updated, skipped_count = bulk_qa_review_tasks(
        db,
        payload.task_ids,
        reviewer_uid=user.uid,
        reviewer_email=user.email,
        qa_status=payload.qa_status,
        qa_note=payload.qa_note,
    )
    return ReviewTaskBulkQaResponse(
        requested_count=len(payload.task_ids),
        updated_count=len(updated),
        skipped_count=skipped_count,
        tasks=[serialize_review_task(task) for task in updated],
    )


@router.post("/review-tasks/bulk/promotion/close", response_model=ReviewTaskBulkPromotionResponse)
def bulk_close_logged_review_tasks_endpoint(
    payload: ReviewTaskBulkPromotionRequest,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_authenticated_user),
) -> ReviewTaskBulkPromotionResponse:
    return bulk_close_logged_review_tasks(
        db,
        payload.task_ids,
        reviewer_uid=user.uid,
        reviewer_email=user.email,
    )


@router.get("/review-tasks/bridge", response_model=ReviewTaskBridgeSummaryResponse)
def review_task_bridge_summary_endpoint(
    _: AuthenticatedUser = Depends(require_authenticated_user),
) -> ReviewTaskBridgeSummaryResponse:
    return get_review_task_bridge_summary()


@router.post("/review-tasks/bridge/sync", response_model=ReviewTaskBridgeSyncResponse)
def review_task_bridge_sync_endpoint(
    _: AuthenticatedUser = Depends(require_authenticated_user),
) -> ReviewTaskBridgeSyncResponse:
    return sync_review_task_bridge(refresh_review_report=True)


@router.post("/jobs/{job_id}/review-tasks/sync", response_model=ReviewTaskSyncResponse)
def sync_review_tasks_endpoint(
    job_id: str,
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(require_authenticated_user),
) -> ReviewTaskSyncResponse:
    job = get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return sync_review_tasks_for_job(db, job)


@router.post("/review-tasks/{task_id}/claim", response_model=ReviewTaskResponse)
def claim_review_task_endpoint(
    task_id: int,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_authenticated_user),
) -> ReviewTaskResponse:
    task = get_review_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Review task not found.")
    if task.status == "submitted":
        raise HTTPException(status_code=409, detail="Submitted review tasks cannot be claimed again.")
    if task.reviewer_uid and task.reviewer_uid != user.uid and task.status == "claimed":
        raise HTTPException(status_code=409, detail="This review task is already claimed by another reviewer.")
    return serialize_review_task(claim_review_task(db, task, reviewer_uid=user.uid, reviewer_email=user.email))


@router.post("/review-tasks/{task_id}/submit", response_model=ReviewTaskResponse)
def submit_review_task_endpoint(
    task_id: int,
    payload: ReviewTaskSubmissionRequest,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_authenticated_user),
) -> ReviewTaskResponse:
    task = get_review_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Review task not found.")
    if task.status == "submitted":
        raise HTTPException(status_code=409, detail="This review task has already been submitted.")
    if task.reviewer_uid and task.reviewer_uid != user.uid:
        raise HTTPException(status_code=403, detail="Only the claiming reviewer can submit this task.")
    updated = submit_review_task(
        db,
        task,
        reviewer_uid=user.uid,
        reviewer_email=user.email,
        decision=payload.decision,
        category_direction=payload.category_direction,
        matched_description=payload.matched_description,
        rate=payload.rate,
        reviewer_note=payload.reviewer_note,
    )
    return serialize_review_task(updated)


@router.post("/review-tasks/{task_id}/qa", response_model=ReviewTaskResponse)
def qa_review_task_endpoint(
    task_id: int,
    payload: ReviewTaskQaRequest,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_authenticated_user),
) -> ReviewTaskResponse:
    task = get_review_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Review task not found.")
    if task.status != "submitted":
        raise HTTPException(status_code=409, detail="Only submitted review tasks can move into QA states.")
    if payload.qa_status.strip().lower() not in {"approved", "rejected", "escalated"}:
        raise HTTPException(status_code=400, detail="QA status must be approved, rejected, or escalated.")
    updated = qa_review_task(
        db,
        task,
        reviewer_uid=user.uid,
        reviewer_email=user.email,
        qa_status=payload.qa_status,
        qa_note=payload.qa_note,
    )
    return serialize_review_task(updated)

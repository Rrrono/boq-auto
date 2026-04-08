"""Reviewer task workflow routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import AuthenticatedUser, require_authenticated_user
from app.db import get_db
from app.models.job import (
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
    mine: bool = Query(default=False),
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_authenticated_user),
) -> list[ReviewTaskResponse]:
    reviewer_uid = user.uid if mine else None
    tasks = list_review_tasks(db, status=status, reviewer_uid=reviewer_uid)
    if qa_status:
        tasks = [task for task in tasks if task.qa_status == qa_status]
    if promotion_status:
        tasks = [task for task in tasks if task.promotion_status == promotion_status]
    return [serialize_review_task(task) for task in tasks]


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

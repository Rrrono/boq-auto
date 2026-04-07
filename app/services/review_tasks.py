"""Review task generation and workflow helpers."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.job import ReviewTaskResponse, ReviewTaskSyncResponse
from app.orm_models import Job, JobRun, ReviewTask


def _row_key(item: dict) -> str:
    sheet_name = str(item.get("sheet_name") or "").strip()
    row_number = int(item.get("row_number") or 0)
    description = str(item.get("description") or "").strip()
    return f"{sheet_name}:{row_number}:{description}".strip()


def _should_create_task(item: dict) -> bool:
    decision = str(item.get("decision") or "").strip().lower()
    review_flag = bool(item.get("review_flag") or False)
    return decision in {"review", "unmatched"} or review_flag


def serialize_review_task(task: ReviewTask) -> ReviewTaskResponse:
    flag_reasons = json.loads(task.flag_reasons_json or "[]")
    if not isinstance(flag_reasons, list):
        flag_reasons = []
    return ReviewTaskResponse(
        id=task.id,
        job_id=task.job_id,
        job_run_id=task.job_run_id,
        status=task.status,
        source_row_key=task.source_row_key,
        sheet_name=task.sheet_name,
        row_number=task.row_number,
        description=task.description,
        matched_description=task.matched_description,
        unit=task.unit,
        decision=task.decision,
        confidence_score=task.confidence_score,
        confidence_band=task.confidence_band,
        flag_reasons=[str(reason) for reason in flag_reasons],
        reviewer_uid=task.reviewer_uid,
        reviewer_email=task.reviewer_email,
        submitted_decision=task.submitted_decision,
        submitted_match_description=task.submitted_match_description,
        submitted_rate=task.submitted_rate,
        reviewer_note=task.reviewer_note,
        submitted_at=task.submitted_at,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


def sync_review_tasks_for_job(db: Session, job: Job) -> ReviewTaskSyncResponse:
    latest_run = next(iter(sorted(job.runs, key=lambda item: item.created_at, reverse=True)), None)
    if latest_run is None:
        return ReviewTaskSyncResponse(job_id=job.id, synced_count=0, open_count=0, tasks=[])

    payload = json.loads(latest_run.result_payload or "{}")
    items = payload.get("items", [])
    synced_count = 0
    now = datetime.now(timezone.utc)

    for item in items:
        if not isinstance(item, dict) or not _should_create_task(item):
            continue

        source_row_key = _row_key(item)
        if not source_row_key:
            continue

        task = (
            db.query(ReviewTask)
            .filter(ReviewTask.job_run_id == latest_run.id, ReviewTask.source_row_key == source_row_key)
            .first()
        )
        if task is None:
            task = ReviewTask(
                job_id=job.id,
                job_run_id=latest_run.id,
                source_row_key=source_row_key,
            )
            db.add(task)
            task.status = "open"
        task.sheet_name = str(item.get("sheet_name") or "")
        task.row_number = int(item.get("row_number") or 0)
        task.description = str(item.get("description") or "")
        task.matched_description = str(item.get("matched_description") or "")
        task.unit = str(item.get("unit") or "")
        task.decision = str(item.get("decision") or "review")
        task.confidence_score = float(item.get("confidence_score") or 0.0)
        task.confidence_band = str(item.get("confidence_band") or "very_low")
        task.flag_reasons_json = json.dumps(item.get("flag_reasons") or [], ensure_ascii=True)
        task.updated_at = now
        synced_count += 1

    db.commit()
    tasks = (
        db.query(ReviewTask)
        .filter(ReviewTask.job_id == job.id, ReviewTask.job_run_id == latest_run.id)
        .order_by(ReviewTask.created_at.asc())
        .all()
    )
    open_count = sum(1 for task in tasks if task.status != "submitted")
    return ReviewTaskSyncResponse(
        job_id=job.id,
        synced_count=synced_count,
        open_count=open_count,
        tasks=[serialize_review_task(task) for task in tasks],
    )


def list_review_tasks(db: Session, *, status: str | None = None, reviewer_uid: str | None = None) -> list[ReviewTask]:
    query = db.query(ReviewTask).order_by(ReviewTask.updated_at.desc(), ReviewTask.created_at.desc())
    if status:
        query = query.filter(ReviewTask.status == status)
    if reviewer_uid:
        query = query.filter(ReviewTask.reviewer_uid == reviewer_uid)
    return list(query.all())


def get_review_task(db: Session, task_id: int) -> ReviewTask | None:
    return db.query(ReviewTask).filter(ReviewTask.id == task_id).first()


def claim_review_task(db: Session, task: ReviewTask, reviewer_uid: str, reviewer_email: str | None) -> ReviewTask:
    task.status = "claimed"
    task.reviewer_uid = reviewer_uid
    task.reviewer_email = reviewer_email or ""
    task.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(task)
    return task


def submit_review_task(
    db: Session,
    task: ReviewTask,
    reviewer_uid: str,
    reviewer_email: str | None,
    *,
    decision: str,
    matched_description: str,
    rate: float | None,
    reviewer_note: str,
) -> ReviewTask:
    task.status = "submitted"
    task.reviewer_uid = reviewer_uid
    task.reviewer_email = reviewer_email or ""
    task.submitted_decision = decision.strip().lower()
    task.submitted_match_description = matched_description.strip()
    task.submitted_rate = rate
    task.reviewer_note = reviewer_note.strip()
    now = datetime.now(timezone.utc)
    task.submitted_at = now
    task.updated_at = now
    db.commit()
    db.refresh(task)
    return task

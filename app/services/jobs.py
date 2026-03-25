"""Job workflow service layer."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.job import JobResponse
from app.orm_models import Job, JobFile, JobRun
from app.services.cost_engine import process_boq_upload
from app.services.job_storage import materialize_uri, store_job_file


def create_job(db: Session, title: str, region: str) -> Job:
    job = Job(id=str(uuid4()), title=title.strip(), region=region.strip(), status="created")
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def list_jobs(db: Session) -> list[Job]:
    return list(db.query(Job).order_by(Job.created_at.desc()).all())


def get_job(db: Session, job_id: str) -> Job | None:
    return db.query(Job).filter(Job.id == job_id).first()


def add_job_file(db: Session, job: Job, file_type: str, filename: str, content_type: str, content: bytes) -> JobFile:
    storage_uri = store_job_file(job.id, file_type, filename, content)
    file_row = JobFile(
        job_id=job.id,
        file_type=file_type,
        filename=filename,
        storage_uri=storage_uri,
        content_type=content_type or "",
    )
    job.updated_at = datetime.now(timezone.utc)
    if file_type == "boq":
        job.status = "file_uploaded"
    db.add(file_row)
    db.commit()
    db.refresh(file_row)
    return file_row


def price_job_boq(db: Session, job: Job) -> tuple[Job, dict]:
    boq_file = (
        db.query(JobFile)
        .filter(JobFile.job_id == job.id, JobFile.file_type == "boq")
        .order_by(JobFile.created_at.desc())
        .first()
    )
    if boq_file is None:
        raise ValueError("No BOQ file has been uploaded for this job.")

    with TemporaryDirectory(prefix="boq_auto_job_") as temp_dir:
        temp_root = Path(temp_dir)
        local_input = materialize_uri(boq_file.storage_uri, temp_root / boq_file.filename)
        result = process_boq_upload(file_bytes=local_input.read_bytes(), filename=boq_file.filename, region=job.region)

    run = JobRun(
        job_id=job.id,
        run_type="price_boq",
        status="completed",
        processed=result.summary.item_count,
        matched=result.summary.matched_count,
        flagged=result.summary.flagged_count,
        total_cost=result.summary.total_cost,
        currency=result.summary.currency,
        output_storage_uri=result.output_storage_uri or "",
        audit_storage_uri=result.audit_storage_uri or "",
        result_payload=json.dumps(result.model_dump(mode="json"), ensure_ascii=True),
    )
    job.status = "priced"
    job.updated_at = datetime.now(timezone.utc)
    db.add(run)
    db.commit()
    db.refresh(run)
    db.refresh(job)
    return job, result.model_dump(mode="json")


def serialize_job(job: Job) -> JobResponse:
    return JobResponse(
        id=job.id,
        title=job.title,
        region=job.region,
        status=job.status,
        created_at=job.created_at,
        updated_at=job.updated_at,
        files=[
            {
                "id": file_row.id,
                "file_type": file_row.file_type,
                "filename": file_row.filename,
                "storage_uri": file_row.storage_uri,
                "content_type": file_row.content_type,
                "created_at": file_row.created_at,
            }
            for file_row in sorted(job.files, key=lambda item: item.created_at)
        ],
        runs=[
            {
                "id": run.id,
                "run_type": run.run_type,
                "status": run.status,
                "processed": run.processed,
                "matched": run.matched,
                "flagged": run.flagged,
                "total_cost": run.total_cost,
                "currency": run.currency,
                "output_storage_uri": run.output_storage_uri,
                "audit_storage_uri": run.audit_storage_uri,
                "created_at": run.created_at,
            }
            for run in sorted(job.runs, key=lambda item: item.created_at, reverse=True)
        ],
    )

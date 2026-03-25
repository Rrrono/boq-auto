"""Job workflow routes for the Phase 1 web platform."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.job import JobCreateRequest, JobPricingResponse, JobResponse
from app.services.jobs import add_job_file, create_job, get_job, list_jobs, price_job_boq, serialize_job


router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobResponse)
def create_job_endpoint(payload: JobCreateRequest, db: Session = Depends(get_db)) -> JobResponse:
    job = create_job(db, payload.title, payload.region)
    return serialize_job(job)


@router.get("", response_model=list[JobResponse])
def list_jobs_endpoint(db: Session = Depends(get_db)) -> list[JobResponse]:
    return [serialize_job(job) for job in list_jobs(db)]


@router.get("/{job_id}", response_model=JobResponse)
def get_job_endpoint(job_id: str, db: Session = Depends(get_db)) -> JobResponse:
    job = get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return serialize_job(job)


@router.post("/{job_id}/files", response_model=JobResponse)
async def upload_job_file(
    job_id: str,
    file_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> JobResponse:
    job = get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    add_job_file(db, job, file_type=file_type.strip().lower(), filename=file.filename or "upload.bin", content_type=file.content_type or "", content=content)
    db.refresh(job)
    return serialize_job(job)


@router.post("/{job_id}/price-boq", response_model=JobPricingResponse)
def price_job_boq_endpoint(job_id: str, db: Session = Depends(get_db)) -> JobPricingResponse:
    job = get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    try:
        refreshed_job, pricing = price_job_boq(db, job)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return JobPricingResponse(job=serialize_job(refreshed_job), pricing=pricing)


@router.get("/{job_id}/results")
def get_job_results_endpoint(job_id: str, db: Session = Depends(get_db)) -> dict:
    job = get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    latest_run = next(iter(sorted(job.runs, key=lambda item: item.created_at, reverse=True)), None)
    if latest_run is None:
        raise HTTPException(status_code=404, detail="No job results available yet.")
    import json

    return json.loads(latest_run.result_payload)

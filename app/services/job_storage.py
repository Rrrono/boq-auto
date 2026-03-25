"""Storage helpers for persisted job inputs and outputs."""

from __future__ import annotations

import os
from pathlib import Path

from app.services.storage import download_gcs_uri


LOCAL_JOB_STORAGE_ROOT = Path(os.getenv("BOQ_AUTO_LOCAL_STORAGE_ROOT", "/tmp/boq_auto_jobs"))


def store_job_file(job_id: str, file_type: str, filename: str, content: bytes) -> str:
    bucket_name = os.getenv("BOQ_AUTO_GCS_BUCKET", "").strip()
    if bucket_name:
        from google.cloud import storage  # type: ignore

        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob_name = f"jobs/{job_id}/inputs/{file_type}/{filename}"
        bucket.blob(blob_name).upload_from_string(content)
        return f"gs://{bucket_name}/{blob_name}"

    destination = LOCAL_JOB_STORAGE_ROOT / job_id / "inputs" / file_type / filename
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)
    return str(destination)


def materialize_uri(uri: str, destination: Path) -> Path:
    if uri.startswith("gs://"):
        return download_gcs_uri(uri, destination)
    source = Path(uri)
    if not source.exists():
        raise FileNotFoundError(f"Stored file not found: {uri}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(source.read_bytes())
    return destination

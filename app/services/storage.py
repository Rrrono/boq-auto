"""Optional cloud storage helpers for persisting API artifacts and runtime data."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path


LOGGER = logging.getLogger("boq_auto.api.storage")


@dataclass(slots=True)
class StoredArtifacts:
    input_storage_uri: str | None = None
    output_storage_uri: str | None = None
    audit_storage_uri: str | None = None


def download_gcs_uri(gcs_uri: str, destination: Path) -> Path:
    """Download a GCS object to a local destination path."""
    bucket_name, blob_name = _split_gcs_uri(gcs_uri)
    try:
        from google.cloud import storage  # type: ignore
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("google-cloud-storage is required for GCS-backed database access.") from exc

    destination.parent.mkdir(parents=True, exist_ok=True)
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    if not blob.exists():
        raise FileNotFoundError(f"GCS object not found: {gcs_uri}")
    blob.download_to_filename(str(destination))
    return destination


def persist_artifacts(
    *,
    request_id: str,
    source_filename: str,
    input_bytes: bytes,
    output_bytes: bytes,
    audit_json_path: Path | None,
) -> StoredArtifacts:
    """Persist request artifacts to GCS when configured, else no-op."""
    bucket_name = os.getenv("BOQ_AUTO_GCS_BUCKET", "").strip()
    if not bucket_name:
        return StoredArtifacts()

    try:
        from google.cloud import storage  # type: ignore
    except Exception:  # pragma: no cover - optional dependency
        LOGGER.exception("google-cloud-storage is not installed; skipping artifact persistence")
        return StoredArtifacts()

    client = storage.Client()
    bucket = client.bucket(bucket_name)
    prefix = os.getenv("BOQ_AUTO_GCS_PREFIX", "boq-api").strip().strip("/")

    input_blob_name = f"{prefix}/{request_id}/input/{source_filename}"
    output_blob_name = f"{prefix}/{request_id}/output/{Path(source_filename).stem}_processed.xlsx"
    audit_blob_name = f"{prefix}/{request_id}/audit/{Path(source_filename).stem}_audit.json"

    bucket.blob(input_blob_name).upload_from_string(
        input_bytes,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    bucket.blob(output_blob_name).upload_from_string(
        output_bytes,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    audit_uri: str | None = None
    if audit_json_path and audit_json_path.exists():
        bucket.blob(audit_blob_name).upload_from_filename(str(audit_json_path), content_type="application/json")
        audit_uri = f"gs://{bucket_name}/{audit_blob_name}"

    return StoredArtifacts(
        input_storage_uri=f"gs://{bucket_name}/{input_blob_name}",
        output_storage_uri=f"gs://{bucket_name}/{output_blob_name}",
        audit_storage_uri=audit_uri,
    )


def _split_gcs_uri(gcs_uri: str) -> tuple[str, str]:
    normalized = gcs_uri.strip()
    if not normalized.startswith("gs://"):
        raise ValueError(f"Expected a gs:// URI, received: {gcs_uri}")
    remainder = normalized[5:]
    if "/" not in remainder:
        raise ValueError(f"GCS URI must include an object path: {gcs_uri}")
    bucket_name, blob_name = remainder.split("/", 1)
    return bucket_name, blob_name

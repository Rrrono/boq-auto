"""Health check route."""

from __future__ import annotations

from fastapi import APIRouter


router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    """Basic liveness endpoint for Cloud Run."""
    return {"status": "ok"}

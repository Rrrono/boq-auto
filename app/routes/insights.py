"""Insight endpoints for price checking and review-first knowledge workflows."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.insights import KnowledgeQueueResponse, PriceCheckResponse
from app.services.insights import build_knowledge_queue, search_price_observations


router = APIRouter(tags=["insights"])


@router.get("/price-check", response_model=PriceCheckResponse)
def price_check_endpoint(
    q: str = Query(default="", description="Free-text search phrase"),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> PriceCheckResponse:
    return search_price_observations(db, q, limit=limit)


@router.get("/knowledge/candidates", response_model=KnowledgeQueueResponse)
def knowledge_candidates_endpoint(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> KnowledgeQueueResponse:
    return build_knowledge_queue(db, limit=limit)

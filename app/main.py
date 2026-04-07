"""FastAPI entrypoint for the BOQ AUTO cloud backend."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import init_db
from app.routes.boq import router as boq_router
from app.routes.health import router as health_router
from app.routes.insights import router as insights_router
from app.routes.jobs import router as jobs_router
from app.routes.review_tasks import router as review_tasks_router
from app.settings import load_settings


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
    settings = load_settings()
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    app = FastAPI(
        title="BOQ AUTO API",
        version="0.1.0",
        description="Cloud-native BOQ processing backend for Excel uploads.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(boq_router)
    app.include_router(jobs_router)
    app.include_router(insights_router)
    app.include_router(review_tasks_router)
    return app


app = create_app()

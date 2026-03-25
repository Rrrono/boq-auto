"""FastAPI entrypoint for the BOQ AUTO cloud backend."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import init_db
from app.routes.boq import router as boq_router
from app.routes.health import router as health_router
from app.routes.insights import router as insights_router
from app.routes.jobs import router as jobs_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
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
    app.include_router(health_router)
    app.include_router(boq_router)
    app.include_router(jobs_router)
    app.include_router(insights_router)
    return app


app = create_app()

"""ORM models for the Phase 1 BOQ AUTO web platform."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp for ORM defaults."""
    return datetime.now(timezone.utc)


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    region: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="created", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    files: Mapped[list["JobFile"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    runs: Mapped[list["JobRun"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    review_tasks: Mapped[list["ReviewTask"]] = relationship(back_populates="job", cascade="all, delete-orphan")


class JobFile(Base):
    __tablename__ = "job_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), nullable=False, index=True)
    file_type: Mapped[str] = mapped_column(String(64), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_uri: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    job: Mapped[Job] = relationship(back_populates="files")


class JobRun(Base):
    __tablename__ = "job_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), nullable=False, index=True)
    run_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="completed", nullable=False)
    processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    matched: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    flagged: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    currency: Mapped[str] = mapped_column(String(16), default="KES", nullable=False)
    output_storage_uri: Mapped[str] = mapped_column(Text, default="", nullable=False)
    audit_storage_uri: Mapped[str] = mapped_column(Text, default="", nullable=False)
    result_payload: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    job: Mapped[Job] = relationship(back_populates="runs")
    review_tasks: Mapped[list["ReviewTask"]] = relationship(back_populates="job_run", cascade="all, delete-orphan")


class ReviewTask(Base):
    __tablename__ = "review_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), nullable=False, index=True)
    job_run_id: Mapped[int] = mapped_column(ForeignKey("job_runs.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="open", nullable=False, index=True)
    source_row_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    sheet_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    row_number: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    matched_description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    unit: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    decision: Mapped[str] = mapped_column(String(32), default="review", nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    confidence_band: Mapped[str] = mapped_column(String(32), default="very_low", nullable=False)
    flag_reasons_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    reviewer_uid: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    reviewer_email: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    submitted_decision: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    submitted_match_description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    submitted_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    reviewer_note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    job: Mapped[Job] = relationship(back_populates="review_tasks")
    job_run: Mapped[JobRun] = relationship(back_populates="review_tasks")

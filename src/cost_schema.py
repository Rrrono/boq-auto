"""Normalized cost-data schema and lightweight SQLite repository."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import json
import sqlite3
from typing import Any
from uuid import uuid4

from openpyxl import Workbook, load_workbook

from src.ingestion import ALIASES_HEADERS, RATE_LIBRARY_HEADERS, append_row, ensure_sheet_headers
from src.normalizer import normalize_text, normalize_unit
from src.utils import ensure_parent, safe_float


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def schema_database_path(database_path: str | Path) -> Path:
    path = Path(database_path)
    if path.suffix.lower() == ".sqlite":
        return path
    return path.with_suffix(".sqlite")


@dataclass(slots=True)
class CostSource:
    id: str
    name: str
    version: str
    file_path: str
    uploaded_at: str


@dataclass(slots=True)
class CostItem:
    id: str
    code: str
    description: str
    normalized_description: str
    unit: str
    category: str
    subcategory: str
    material: str
    keywords: list[str]
    rate: float
    source_id: str
    created_at: str


@dataclass(slots=True)
class CostAlias:
    id: str
    item_id: str
    alias: str


@dataclass(slots=True)
class IngestionLog:
    id: str
    source_id: str
    status: str
    message: str
    created_at: str


@dataclass(slots=True)
class ItemEmbedding:
    item_id: str
    embedding: list[float]
    model: str
    created_at: str


@dataclass(slots=True)
class MatchFeedback:
    id: str
    query: str
    selected_item_id: str
    rejected_item_ids: list[str]
    created_at: str


class CostDatabase:
    """SQLite-backed normalized cost-data store with Excel compatibility helpers."""

    def __init__(self, path: str | Path) -> None:
        self.path = schema_database_path(path)

    def initialize(self) -> Path:
        ensure_parent(self.path)
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sources (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    version TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    uploaded_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS items (
                    id TEXT PRIMARY KEY,
                    code TEXT NOT NULL,
                    description TEXT NOT NULL,
                    normalized_description TEXT NOT NULL,
                    unit TEXT NOT NULL,
                    category TEXT NOT NULL,
                    subcategory TEXT NOT NULL,
                    material TEXT NOT NULL DEFAULT '',
                    keywords TEXT NOT NULL DEFAULT '[]',
                    rate REAL NOT NULL,
                    source_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(source_id) REFERENCES sources(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS aliases (
                    id TEXT PRIMARY KEY,
                    item_id TEXT NOT NULL,
                    alias TEXT NOT NULL,
                    FOREIGN KEY(item_id) REFERENCES items(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ingestion_logs (
                    id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    message TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(source_id) REFERENCES sources(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS item_embeddings (
                    item_id TEXT PRIMARY KEY,
                    embedding TEXT NOT NULL,
                    model TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(item_id) REFERENCES items(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS match_feedback (
                    id TEXT PRIMARY KEY,
                    query TEXT NOT NULL,
                    selected_item_id TEXT NOT NULL,
                    rejected_item_ids TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            existing_columns = {row[1] for row in conn.execute("PRAGMA table_info(items)")}
            if "material" not in existing_columns:
                conn.execute("ALTER TABLE items ADD COLUMN material TEXT NOT NULL DEFAULT ''")
            if "keywords" not in existing_columns:
                conn.execute("ALTER TABLE items ADD COLUMN keywords TEXT NOT NULL DEFAULT '[]'")
        return self.path

    def register_source(self, name: str, version: str, file_path: str) -> CostSource:
        self.initialize()
        source = CostSource(
            id=str(uuid4()),
            name=name.strip() or "Unnamed Source",
            version=version.strip() or "v1",
            file_path=file_path,
            uploaded_at=utc_now_iso(),
        )
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                "INSERT INTO sources (id, name, version, file_path, uploaded_at) VALUES (?, ?, ?, ?, ?)",
                (source.id, source.name, source.version, source.file_path, source.uploaded_at),
            )
        return source

    def insert_items(self, items: list[CostItem], aliases_by_item: dict[str, list[str]] | None = None) -> int:
        self.initialize()
        aliases_by_item = aliases_by_item or {}
        with sqlite3.connect(self.path) as conn:
            for item in items:
                conn.execute(
                    """
                    INSERT INTO items (id, code, description, normalized_description, unit, category, subcategory, material, keywords, rate, source_id, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item.id,
                        item.code,
                        item.description,
                        item.normalized_description,
                        item.unit,
                        item.category,
                        item.subcategory,
                        item.material,
                        json.dumps(item.keywords, ensure_ascii=True),
                        item.rate,
                        item.source_id,
                        item.created_at,
                    ),
                )
                for alias in aliases_by_item.get(item.id, []):
                    conn.execute(
                        "INSERT INTO aliases (id, item_id, alias) VALUES (?, ?, ?)",
                        (str(uuid4()), item.id, alias),
                    )
        return len(items)

    def log_ingestion(self, source_id: str, status: str, message: str) -> IngestionLog:
        self.initialize()
        record = IngestionLog(
            id=str(uuid4()),
            source_id=source_id,
            status=status,
            message=message,
            created_at=utc_now_iso(),
        )
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                "INSERT INTO ingestion_logs (id, source_id, status, message, created_at) VALUES (?, ?, ?, ?, ?)",
                (record.id, record.source_id, record.status, record.message, record.created_at),
            )
        return record

    def fetch_items(self) -> list[CostItem]:
        self.initialize()
        with sqlite3.connect(self.path) as conn:
            rows = conn.execute(
                """
                SELECT id, code, description, normalized_description, unit, category, subcategory, material, keywords, rate, source_id, created_at
                FROM items
                ORDER BY created_at DESC
                """
            ).fetchall()
        return [
            CostItem(
                id=str(row[0]),
                code=str(row[1]),
                description=str(row[2]),
                normalized_description=str(row[3]),
                unit=str(row[4]),
                category=str(row[5]),
                subcategory=str(row[6]),
                material=str(row[7]),
                keywords=list(json.loads(row[8] or "[]")),
                rate=float(row[9]),
                source_id=str(row[10]),
                created_at=str(row[11]),
            )
            for row in rows
        ]

    def fetch_ingestion_logs(self) -> list[IngestionLog]:
        self.initialize()
        with sqlite3.connect(self.path) as conn:
            rows = conn.execute(
                """
                SELECT id, source_id, status, message, created_at
                FROM ingestion_logs
                ORDER BY created_at DESC
                """
            ).fetchall()
        return [IngestionLog(*row) for row in rows]

    def fetch_aliases(self) -> list[CostAlias]:
        self.initialize()
        with sqlite3.connect(self.path) as conn:
            rows = conn.execute("SELECT id, item_id, alias FROM aliases ORDER BY alias ASC").fetchall()
        return [CostAlias(*row) for row in rows]

    def save_embedding(self, item_id: str, embedding: list[float], model: str) -> None:
        self.initialize()
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                """
                INSERT INTO item_embeddings (item_id, embedding, model, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(item_id) DO UPDATE SET
                    embedding=excluded.embedding,
                    model=excluded.model,
                    created_at=excluded.created_at
                """,
                (item_id, json.dumps(embedding), model, utc_now_iso()),
            )

    def fetch_embedding_lookup(self) -> dict[str, list[float]]:
        self.initialize()
        with sqlite3.connect(self.path) as conn:
            rows = conn.execute(
                """
                SELECT items.code, item_embeddings.embedding
                FROM item_embeddings
                JOIN items ON items.id = item_embeddings.item_id
                """
            ).fetchall()
        return {str(code): list(json.loads(embedding_json)) for code, embedding_json in rows}

    def clear_embeddings(self) -> int:
        self.initialize()
        with sqlite3.connect(self.path) as conn:
            before = conn.execute("SELECT COUNT(*) FROM item_embeddings").fetchone()
            conn.execute("DELETE FROM item_embeddings")
        return int((before or [0])[0])

    def fetch_embedding_stats(self) -> dict[str, Any]:
        self.initialize()
        with sqlite3.connect(self.path) as conn:
            total_items = int((conn.execute("SELECT COUNT(*) FROM items").fetchone() or [0])[0])
            embedded_items = int((conn.execute("SELECT COUNT(*) FROM item_embeddings").fetchone() or [0])[0])
            last_updated = conn.execute("SELECT MAX(created_at) FROM item_embeddings").fetchone()
        return {
            "total_items": total_items,
            "embedded_items": embedded_items,
            "last_updated": str((last_updated or [""])[0] or ""),
        }

    def fetch_embedding_records(self, limit: int = 20) -> list[dict[str, Any]]:
        self.initialize()
        with sqlite3.connect(self.path) as conn:
            rows = conn.execute(
                """
                SELECT items.code, items.description, item_embeddings.item_id, item_embeddings.model, item_embeddings.created_at
                FROM item_embeddings
                JOIN items ON items.id = item_embeddings.item_id
                ORDER BY item_embeddings.created_at DESC
                LIMIT ?
                """,
                (int(limit),),
            ).fetchall()
        return [
            {
                "code": str(row[0] or ""),
                "description": str(row[1] or ""),
                "item_id": str(row[2] or ""),
                "model": str(row[3] or ""),
                "created_at": str(row[4] or ""),
            }
            for row in rows
        ]

    def log_match_feedback(self, query: str, selected_item_id: str, rejected_item_ids: list[str]) -> MatchFeedback:
        self.initialize()
        record = MatchFeedback(
            id=str(uuid4()),
            query=query,
            selected_item_id=selected_item_id,
            rejected_item_ids=list(rejected_item_ids),
            created_at=utc_now_iso(),
        )
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                "INSERT INTO match_feedback (id, query, selected_item_id, rejected_item_ids, created_at) VALUES (?, ?, ?, ?, ?)",
                (record.id, record.query, record.selected_item_id, json.dumps(record.rejected_item_ids, ensure_ascii=True), record.created_at),
            )
        return record

    def fetch_match_feedback(self) -> list[MatchFeedback]:
        self.initialize()
        with sqlite3.connect(self.path) as conn:
            rows = conn.execute(
                "SELECT id, query, selected_item_id, rejected_item_ids, created_at FROM match_feedback ORDER BY created_at DESC"
            ).fetchall()
        return [
            MatchFeedback(
                id=str(row[0]),
                query=str(row[1]),
                selected_item_id=str(row[2]),
                rejected_item_ids=list(json.loads(row[3] or "[]")),
                created_at=str(row[4]),
            )
            for row in rows
        ]

    def resolve_item_id(self, item_ref: str) -> str:
        self.initialize()
        with sqlite3.connect(self.path) as conn:
            row = conn.execute(
                "SELECT id FROM items WHERE id = ? OR code = ? ORDER BY created_at DESC LIMIT 1",
                (item_ref, item_ref),
            ).fetchone()
        return str(row[0]) if row else ""

    def export_to_excel(self, excel_path: str | Path) -> Path:
        self.initialize()
        target = Path(excel_path)
        workbook = load_workbook(target) if target.exists() else Workbook()
        if "Sheet" in workbook.sheetnames and len(workbook.sheetnames) == 1:
            del workbook["Sheet"]

        rate_sheet = ensure_sheet_headers(workbook, "RateLibrary", RATE_LIBRARY_HEADERS)
        alias_sheet = ensure_sheet_headers(workbook, "Aliases", ALIASES_HEADERS)
        for sheet in (rate_sheet, alias_sheet):
            if sheet.max_row > 1:
                sheet.delete_rows(2, sheet.max_row - 1)

        item_lookup = {item.id: item for item in self.fetch_items()}
        for item in item_lookup.values():
            append_row(
                rate_sheet,
                RATE_LIBRARY_HEADERS,
                {
                    "item_code": item.code,
                    "description": item.description,
                    "normalized_description": item.normalized_description,
                    "section": item.category,
                    "subsection": item.subcategory,
                    "unit": item.unit,
                    "rate": item.rate,
                    "currency": "KES",
                    "region": "",
                    "source": "Normalized Cost Schema",
                    "source_sheet": "items",
                    "source_page": "",
                    "basis": "Exported from normalized schema",
                    "crew_type": "",
                    "plant_type": "",
                    "material_type": "",
                    "keywords": ", ".join(item.keywords),
                    "alias_group": "",
                    "build_up_recipe_id": "",
                    "confidence_hint": 0.0,
                    "notes": "",
                    "active": True,
                },
            )
        for alias in self.fetch_aliases():
            item = item_lookup.get(alias.item_id)
            if item is None:
                continue
            append_row(alias_sheet, ALIASES_HEADERS, {"alias": alias.alias, "canonical_term": item.description, "section_bias": item.category, "notes": ""})
        ensure_parent(target)
        workbook.save(target)
        return target

    def import_excel_database(self, excel_path: str | Path) -> int:
        self.initialize()
        workbook = load_workbook(excel_path, data_only=True)
        if "RateLibrary" not in workbook.sheetnames:
            return 0
        rate_sheet = workbook["RateLibrary"]
        headers = [str(cell.value or "").strip() for cell in next(rate_sheet.iter_rows(min_row=1, max_row=1))]
        source = self.register_source(Path(excel_path).stem, "excel-import", str(excel_path))
        items: list[CostItem] = []
        for row in rate_sheet.iter_rows(min_row=2, values_only=True):
            values = dict(zip(headers, row))
            description = str(values.get("description") or "").strip()
            if not description:
                continue
            items.append(
                CostItem(
                    id=str(uuid4()),
                    code=str(values.get("item_code") or ""),
                    description=description,
                    normalized_description=normalize_text(str(values.get("normalized_description") or description)),
                    unit=normalize_unit(str(values.get("unit") or "")),
                    category=str(values.get("section") or ""),
                    subcategory=str(values.get("subsection") or ""),
                    material=str(values.get("material_type") or ""),
                    keywords=[value.strip() for value in str(values.get("keywords") or "").split(",") if value.strip()],
                    rate=safe_float(values.get("rate")) or 0.0,
                    source_id=source.id,
                    created_at=utc_now_iso(),
                )
            )
        inserted = self.insert_items(items)
        self.log_ingestion(source.id, "completed", f"Imported {inserted} item(s) from Excel database.")
        return inserted


def build_cost_item(
    code: str,
    description: str,
    unit: str,
    category: str,
    subcategory: str,
    material: str,
    keywords: list[str] | None,
    rate: float,
    source_id: str,
) -> CostItem:
    return CostItem(
        id=str(uuid4()),
        code=code.strip(),
        description=description.strip(),
        normalized_description=normalize_text(description),
        unit=normalize_unit(unit),
        category=category.strip(),
        subcategory=subcategory.strip(),
        material=material.strip(),
        keywords=list(keywords or []),
        rate=rate,
        source_id=source_id,
        created_at=utc_now_iso(),
    )


def composed_embedding_text(item: CostItem) -> str:
    """Build the canonical embedding text for a cost item."""

    return " | ".join(
        [
            item.category.strip(),
            item.material.strip(),
            item.description.strip(),
            item.unit.strip(),
        ]
    )

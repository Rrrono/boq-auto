import sqlite3
from pathlib import Path

from openpyxl import Workbook

from src.cost_schema import CostDatabase, build_cost_item, composed_embedding_text, derive_taxonomy_fields, schema_database_path


def test_schema_creation_creates_expected_tables(tmp_path) -> None:
    repository = CostDatabase(tmp_path / "master.xlsx")
    schema_path = repository.initialize()

    assert schema_path == schema_database_path(tmp_path / "master.xlsx")
    with sqlite3.connect(schema_path) as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"sources", "items", "aliases", "ingestion_logs", "item_embeddings", "match_feedback"} <= tables


def test_excel_import_and_export_round_trip(tmp_path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "RateLibrary"
    sheet.append(["item_code", "description", "normalized_description", "section", "subsection", "unit", "rate"])
    sheet.append(["A1", "Excavation", "excavation", "earthworks", "", "m3", 1200])
    alias_sheet = workbook.create_sheet("Aliases")
    alias_sheet.append(["alias", "canonical_term", "section_bias", "notes"])
    source_excel = tmp_path / "source.xlsx"
    workbook.save(source_excel)

    repository = CostDatabase(tmp_path / "master.xlsx")
    inserted = repository.import_excel_database(source_excel)
    exported = repository.export_to_excel(tmp_path / "export.xlsx")

    assert inserted == 1
    assert Path(exported).exists()


def test_insert_items_and_embeddings(tmp_path) -> None:
    repository = CostDatabase(tmp_path / "master.xlsx")
    source = repository.register_source("Manual", "v1", "manual.pdf")
    item = build_cost_item("A1", "Excavation", "m3", "earthworks", "", "soil", ["excavation", "trench"], 1000.0, source.id)
    repository.insert_items([item])
    repository.save_embedding(item.id, [0.1, 0.2, 0.3], "hash-local-v1")
    repository.log_match_feedback("excavate trench", item.id, "accepted")

    lookup = repository.fetch_embedding_lookup()
    assert lookup["A1"] == [0.1, 0.2, 0.3]
    feedback = repository.fetch_match_feedback()[0]
    assert feedback.selected_item_id == item.id
    assert feedback.action == "accepted"
    assert composed_embedding_text(item) == "civil_works | earthworks | earthworks | work_item | civil_general | soil | Excavation | m3"
    assert repository.resolve_item_id("A1") == item.id


def test_taxonomy_fields_are_inferred_for_equipment_and_utilities() -> None:
    equipment = derive_taxonomy_fields(
        description="Motor grader complete with hydraulic ripper or scarifier",
        category="Earthworks",
        subcategory="Plant",
        material="",
    )
    utilities = derive_taxonomy_fields(
        description="HDPE pipe 110 mm including fittings",
        category="Plumbing",
        subcategory="Pipework",
        material="pipe",
    )

    assert equipment["domain"] == "roads"
    assert equipment["work_family"] == "earthworks"
    assert equipment["item_kind"] == "equipment"
    assert equipment["project_context"] == "roads"

    assert utilities["domain"] == "drainage_utilities"
    assert utilities["work_family"] == "piping"
    assert utilities["project_context"] == "water_utilities"

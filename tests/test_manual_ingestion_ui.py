import pandas as pd

from src.manual_parser import ManualItem
from ui.manual_ingestion_page import _coerce_row, _manual_item_from_row, _update_master_rows


def test_manual_ingestion_row_round_trip_preserves_metadata() -> None:
    row = _coerce_row(
        ManualItem(
            code="A1",
            item_name="Excavation",
            unit="m3",
            description="Excavation in normal soil",
            rate=350.0,
            category="earthworks",
            material="soil",
            keywords=["excavation", "soil"],
            aliases=["earth excavation"],
        ),
        row_id=1,
    )

    rebuilt = _manual_item_from_row(row)

    assert rebuilt.code == "A1"
    assert rebuilt.rate == 350.0
    assert rebuilt.category == "earthworks"
    assert rebuilt.material == "soil"
    assert rebuilt.keywords == ["excavation", "soil"]
    assert rebuilt.aliases == ["earth excavation"]


def test_update_master_rows_keeps_hidden_metadata_when_editor_updates_display_fields() -> None:
    parsed_rows = [
        {
            "_row_id": 1,
            "Select": True,
            "Code": "A1",
            "Item Name": "Excavation",
            "Unit": "m3",
            "Description": "Original description",
            "Rate": 350.0,
            "Category": "earthworks",
            "Material": "soil",
            "Keywords": "excavation, soil",
            "Aliases": "earth excavation",
        }
    ]

    edited_df = pd.DataFrame(
        [
            {
                "Select": True,
                "Code": "A1",
                "Item Name": "Excavation",
                "Unit": "m3",
                "Description": "Updated description",
            }
        ],
        index=[1],
    )

    updated = _update_master_rows(edited_df, parsed_rows)

    assert updated[0]["Description"] == "Updated description"
    assert updated[0]["Rate"] == 350.0
    assert updated[0]["Category"] == "earthworks"
    assert updated[0]["Keywords"] == "excavation, soil"

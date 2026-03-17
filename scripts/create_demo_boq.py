"""Create a demo BOQ workbook for BOQ AUTO."""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook


OUTPUT = Path("boq/demo_boq.xlsx")


def make_sheet(workbook: Workbook, title: str, rows: list[list]) -> None:
    """Create a BOQ worksheet and populate it."""
    sheet = workbook.create_sheet(title)
    sheet["A1"] = title
    sheet.append(["", "", "", "", ""])
    sheet.append(["Item Description", "Unit", "Qty", "Rate", "Amount"])
    for row in rows:
        sheet.append(row)


def main() -> None:
    """Generate a usable demo BOQ workbook."""
    workbook = Workbook()
    default = workbook.active
    workbook.remove(default)

    make_sheet(
        workbook,
        "Preliminaries",
        [
            ["Preliminaries", "", "", "", ""],
            ["Preliminaries and general items", "sum", 1, "", ""],
        ],
    )
    make_sheet(
        workbook,
        "Dayworks Plant",
        [
            ["Dayworks", "", "", "", ""],
            ["15 tonne tipper lorry", "day", 4, "", ""],
            ["2 cm/hr dewatering pump", "day", 6, "", ""],
            ["Compressor with drill (250 c.f.m) complete with tools, hoses and steel bits", "day", 2, "", ""],
            ["Concrete vibrator (poker type)", "day", 3, "", ""],
            ["Pick-up truck (1 - 1.5 tonne capacity)", "day", 5, "", ""],
        ],
    )
    make_sheet(
        workbook,
        "Earthworks",
        [
            ["Earthworks", "", "", "", ""],
            ["Excavation in ordinary soil", "m3", 125, "", ""],
            ["Sheep foot roller - 15 tons", "day", 3, "", ""],
            ["Excavator with loader attachment - 1.7 m3", "day", 4, "", ""],
            ["Self-propelled water tanker (6,000-20,000 litres) with pick-up pump", "day", 3, "", ""],
            ["crawler dozers with dozer and hydraulic ripper attachments", "day", 2, "", ""],
            ["motor graders complete with hydraulic ripper or scarifier", "day", 2, "", ""],
        ],
    )
    make_sheet(
        workbook,
        "Concrete Works",
        [
            ["Concrete", "", "", "", ""],
            ["Mass concrete class 15", "m3", 18, "", ""],
            ["Concrete mixer 0.3 - 0.7 m3/min", "day", 2, "", ""],
        ],
    )
    make_sheet(
        workbook,
        "Finishes",
        [
            ["Finishes", "", "", "", ""],
            ["Plaster and render finish to walls", "m2", 220, "", ""],
        ],
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(OUTPUT)
    print(f"Demo BOQ created at {OUTPUT}")


if __name__ == "__main__":
    main()

from src.models import BOQLine, SectionRule
from src.section_inference import classify_sheet_name, infer_section


def test_section_inference_uses_sheet_and_heading_context() -> None:
    rules = [
        SectionRule("earthworks", "Earthworks", 100),
        SectionRule("concrete", "Concrete", 90),
    ]
    row = BOQLine(sheet_name="Bill 3", row_number=10, description="Excavation in ordinary soil")
    section = infer_section("Bill 3", row, ["Earthworks"], rules)
    assert section == "Earthworks"


def test_section_inference_handles_messy_sheet_names() -> None:
    assert classify_sheet_name("BoQ 1 Preliminaries") == "Preliminaries"
    assert classify_sheet_name("Bill No. 3 Earthworks") == "Earthworks"
    assert classify_sheet_name("Contractor's Equipment") == "Dayworks"
    assert classify_sheet_name("Plant Hire") == "Dayworks"

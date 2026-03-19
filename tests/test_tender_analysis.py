from pathlib import Path

from src.config import load_config
from src.boq_drafter import BOQDrafter
from src.boq_gap_checker import BOQGapChecker
from src.clarification_log import ClarificationLogBuilder
from src.requirement_extractor import RequirementExtractor
from src.scope_parser import ScopeParser
from src.tender_models import ScopeSection, TenderDocument, TenderSourceLine
from src.tender_reader import read_tender_document


def test_tender_reader_reads_demo_text_file() -> None:
    document = read_tender_document("tender/demo_tender_notice.txt")
    assert document.document_type == "text"
    assert document.lines
    assert "TENDER FOR PROPOSED HEALTH CENTRE UPGRADE" in document.text


def test_requirement_extractor_finds_security_and_period_requirements() -> None:
    config = load_config()
    document = read_tender_document("tender/demo_tender_notice.txt")
    extractor = RequirementExtractor(config)
    requirements = extractor.extract(document)

    categories = {item.category for item in requirements}
    descriptions = [item.description for item in requirements]

    assert "Securities" in categories
    assert "Periods" in categories
    assert any("2%" in description for description in descriptions)
    assert any("120 days" in description.lower() for description in descriptions)


def test_scope_parser_detects_practical_sections() -> None:
    config = load_config()
    document = read_tender_document("tender/demo_tender_notice.txt")
    parser = ScopeParser(config)
    sections = parser.parse(document)

    names = {section.section_name for section in sections}
    assert "Preliminaries" in names
    assert "Earthworks" in names
    assert "Contractor's Equipment" in names


def test_boq_drafter_creates_review_first_suggestions() -> None:
    config = load_config()
    document = read_tender_document("tender/demo_tender_scope_only.txt")
    sections = ScopeParser(config).parse(document)
    suggestions = BOQDrafter(config).build_suggestions(document, sections)

    assert suggestions
    assert all(item.review_flag is True for item in suggestions)
    assert all(item.quantity_placeholder == "TBD" for item in suggestions)


def test_clarification_builder_flags_unclear_measurement_language() -> None:
    config = load_config()
    document = read_tender_document("tender/demo_tender_scope_only.txt")
    requirements = RequirementExtractor(config).extract(document)
    sections = ScopeParser(config).parse(document)
    clarifications = ClarificationLogBuilder(config).build(document, requirements, sections)

    assert clarifications
    assert any("measurement" in item.action_needed.lower() or "confirm" in item.action_needed.lower() for item in clarifications)


def test_gap_checker_without_boq_stays_review_first() -> None:
    config = load_config()
    document = read_tender_document("tender/demo_tender_scope_only.txt")
    sections = ScopeParser(config).parse(document)
    suggestions = BOQDrafter(config).build_suggestions(document, sections)
    gaps = BOQGapChecker(config).check(sections, suggestions, boq_path=None)

    assert gaps
    assert all(item.review_flag is True for item in gaps)


def test_boq_drafter_filters_headings_definitions_and_consolidates_duplicates() -> None:
    config = load_config()
    document = TenderDocument(
        source_path=Path("tender/test.txt"),
        document_name="test.txt",
        document_type="text",
        title="Test Tender",
        text="",
        lines=[
            TenderSourceLine(source_reference="L1", text="SECTION 5 - EARTHWORKS", line_number=1),
            TenderSourceLine(source_reference="L2", text="Excavate for foundations and cart away surplus material.", line_number=2),
            TenderSourceLine(source_reference="L3", text="and dispose unsuitable material off site.", line_number=3),
            TenderSourceLine(source_reference="L4", text="Earthworks means all work incidental to formation.", line_number=4),
            TenderSourceLine(source_reference="L5", text="Refer to section 7 for details.", line_number=5),
            TenderSourceLine(source_reference="L6", text="Excavation for foundations including disposal of surplus excavated material.", line_number=6),
        ],
    )
    sections = [ScopeSection(section_name="Earthworks", confidence=82.0, source_references=["L1", "L2"], matched_keywords=["earthworks", "excavate"])]

    suggestions = BOQDrafter(config).build_suggestions(document, sections)

    descriptions = [item.description for item in suggestions]
    assert "SECTION 5 - EARTHWORKS" not in descriptions
    assert all("means" not in (item.source_excerpt or "").lower() for item in suggestions)
    assert descriptions.count("Excavation for foundations") == 1
    assert any("disposal" in item.description.lower() for item in suggestions)


def test_boq_drafter_merges_continuations_and_generates_concise_descriptions() -> None:
    config = load_config()
    document = TenderDocument(
        source_path=Path("tender/test.txt"),
        document_name="test.txt",
        document_type="text",
        title="Test Tender",
        text="",
        lines=[
            TenderSourceLine(source_reference="L1", text="Earthworks to excavate foundations,", line_number=1),
            TenderSourceLine(source_reference="L2", text="including disposal of unsuitable material", line_number=2),
            TenderSourceLine(source_reference="L3", text="and backfill with approved selected material.", line_number=3),
        ],
    )
    sections = [ScopeSection(section_name="Earthworks", confidence=80.0, source_references=["L1"], matched_keywords=["earthworks", "excavate"])]

    suggestions = BOQDrafter(config).build_suggestions(document, sections)

    descriptions = {item.description for item in suggestions}
    assert "Excavation for foundations" in descriptions
    assert "Excavation and disposal of unsuitable material" in descriptions
    assert any(item.description == "Fill with approved selected material" for item in suggestions)
    assert all(len(item.description.split()) <= 8 for item in suggestions if "Insert BOQ line items" not in item.description)


def test_boq_drafter_leaves_unit_blank_when_inference_is_weak() -> None:
    config = load_config()
    document = TenderDocument(
        source_path=Path("tender/test.txt"),
        document_name="test.txt",
        document_type="text",
        title="Test Tender",
        text="",
        lines=[TenderSourceLine(source_reference="L1", text="Electrical installation including testing and commissioning.", line_number=1)],
    )
    sections = [ScopeSection(section_name="Electrical", confidence=78.0, source_references=["L1"], matched_keywords=["electrical"])]

    suggestions = BOQDrafter(config).build_suggestions(document, sections)

    assert suggestions
    assert suggestions[0].unit == ""

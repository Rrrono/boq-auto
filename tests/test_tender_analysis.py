from src.config import load_config
from src.boq_drafter import BOQDrafter
from src.boq_gap_checker import BOQGapChecker
from src.clarification_log import ClarificationLogBuilder
from src.requirement_extractor import RequirementExtractor
from src.scope_parser import ScopeParser
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

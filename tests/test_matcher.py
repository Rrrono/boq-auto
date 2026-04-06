from src.matcher import Matcher, MatchingWeights
from src.models import AliasEntry, BOQLine, RateItem


def test_matcher_prefers_section_and_unit_compatible_item() -> None:
    items = [
        RateItem("A", "Concrete vibrator poker type", "concrete vibrator poker", "Concrete", "", "day", 2500, "KES", "Nyanza", "src", "", "", "", "", "", "", "", "", "", 0, "", True),
        RateItem("B", "Pick up truck", "pick up truck", "Dayworks", "", "day", 6500, "KES", "Nyanza", "src", "", "", "", "", "", "", "", "", "", 0, "", True),
    ]
    matcher = Matcher(
        items,
        [AliasEntry("vibrator", "concrete vibrator", "Concrete", "")],
        MatchingWeights(78, 65, 88, 4, 8, 6, 5, 18, 6),
    )
    line = BOQLine(sheet_name="Concrete", row_number=5, description="Concrete vibrator (poker type)", unit="day", inferred_section="Concrete")
    result = matcher.match(line, "Nyanza")
    assert result.matched_item_code == "A"
    assert result.confidence_score >= 78


def test_matcher_returns_alternate_options_for_close_candidates() -> None:
    items = [
        RateItem("A", "15 tonne tipper lorry", "15 ton tipper lorry", "Dayworks", "", "day", 18500, "KES", "Nyanza", "src", "", "", "hire", "", "", "", "", "", "", 0, "", True),
        RateItem("B", "10 tonne tipper lorry", "10 ton tipper lorry", "Dayworks", "", "day", 16200, "KES", "Nyanza", "src", "", "", "hire", "", "", "", "", "", "", 0, "", True),
    ]
    matcher = Matcher(items, [], MatchingWeights(78, 65, 88, 4, 8, 6, 5, 18, 6))
    line = BOQLine(sheet_name="Dayworks", row_number=3, description="15 tonne tipper lorry", unit="day", inferred_section="Dayworks")
    result = matcher.match(line, "Nyanza")
    assert result.matched_item_code == "A"
    assert result.alternate_options


def test_matcher_flags_strong_unit_mismatch() -> None:
    items = [
        RateItem("A", "Mass concrete class 15", "mass concrete class 15", "Concrete", "", "m3", 15200, "KES", "Nyanza", "src", "", "", "supply", "", "", "", "", "", "", 0, "", True),
    ]
    matcher = Matcher(items, [], MatchingWeights(78, 65, 88, 4, 8, 6, 5, 18, 6))
    line = BOQLine(sheet_name="Concrete", row_number=6, description="Mass concrete class 15", unit="m2", inferred_section="Concrete")
    result = matcher.match(line, "Nyanza")
    assert result.review_flag is True
    assert any("unit mismatch" in flag for flag in result.commercial_review_flags)


def test_matcher_uses_spec_attributes_as_extra_signal() -> None:
    items = [
        RateItem("A", "LED light fittings complete", "led light fittings complete", "Electrical", "", "nr", 4500, "KES", "Nairobi", "src", "", "", "", "", "", "lighting", "light, led, driver, ceiling", "", "", 0, "", True),
        RateItem("B", "Socket outlet point complete", "socket outlet point complete", "Electrical", "", "nr", 2800, "KES", "Nairobi", "src", "", "", "", "", "", "power", "socket, outlet", "", "", 0, "", True),
    ]
    matcher = Matcher(items, [], MatchingWeights(78, 65, 88, 4, 8, 6, 5, 18, 6))
    line = BOQLine(
        sheet_name="Pricing Handoff",
        row_number=2,
        description="Light fittings complete",
        unit="nr",
        spec_attributes="600 x 600; LED; complete with drivers; ceiling mounted",
        inferred_section="Electrical",
    )

    result = matcher.match(line, "Nairobi")

    assert result.matched_item_code == "A"
    assert any("attribute=" in note for note in result.rationale)


def test_matcher_downgrades_generic_candidate_matches() -> None:
    items = [
        RateItem("A", "General electrical works", "general electrical works", "Electrical", "", "sum", 250000, "KES", "Nairobi", "src", "", "", "", "", "", "", "", "", "", 0, "", True),
    ]
    matcher = Matcher(items, [], MatchingWeights(78, 65, 88, 4, 8, 6, 5, 18, 6))
    line = BOQLine(
        sheet_name="Electrical",
        row_number=7,
        description="Electrical light fittings installation",
        unit="sum",
        inferred_section="Electrical",
    )

    result = matcher.match(line, "Nairobi")

    assert result.generic_match_flag is True
    assert "generic_match" in result.flag_reasons
    assert result.decision in {"review", "unmatched"}


def test_matcher_flags_category_mismatch_for_text_similar_weak_cluster() -> None:
    items = [
        RateItem("A", "Concrete testing and commissioning", "concrete testing and commissioning", "Concrete", "", "item", 18000, "KES", "Nairobi", "src", "", "", "", "", "", "", "test, concrete", "", "", 0, "", True),
    ]
    matcher = Matcher(items, [], MatchingWeights(78, 65, 88, 4, 8, 6, 5, 18, 6))
    line = BOQLine(
        sheet_name="Electrical",
        row_number=10,
        description="Electrical testing and commissioning",
        unit="item",
        inferred_section="Electrical",
    )

    result = matcher.match(line, "Nairobi")

    assert result.category_mismatch_flag is True
    assert "category_mismatch" in result.flag_reasons
    assert result.decision in {"review", "unmatched"}


def test_matcher_treats_electrical_support_as_electrical_family() -> None:
    items = [
        RateItem("A", "Electrical supply and install transformer", "electrical supply and install transformer", "Electrical", "", "item", 185000, "KES", "Nairobi", "src", "", "", "", "", "", "", "transformer, electrical", "", "", 0, "", True),
    ]
    matcher = Matcher(items, [], MatchingWeights(78, 65, 88, 4, 8, 6, 5, 18, 6))
    line = BOQLine(
        sheet_name="Electrical Support",
        row_number=8,
        description="Supply and install transformer complete",
        unit="item",
        inferred_section="Electrical",
    )

    result = matcher.match(line, "Nairobi")

    assert result.category_mismatch_flag is False
    assert result.decision in {"matched", "review"}

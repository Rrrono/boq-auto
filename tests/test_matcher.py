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
        MatchingWeights(78, 65, 88, 4, 8, 6, 5, 18),
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
    matcher = Matcher(items, [], MatchingWeights(78, 65, 88, 4, 8, 6, 5, 18))
    line = BOQLine(sheet_name="Dayworks", row_number=3, description="15 tonne tipper lorry", unit="day", inferred_section="Dayworks")
    result = matcher.match(line, "Nyanza")
    assert result.matched_item_code == "A"
    assert result.alternate_options


def test_matcher_flags_strong_unit_mismatch() -> None:
    items = [
        RateItem("A", "Mass concrete class 15", "mass concrete class 15", "Concrete", "", "m3", 15200, "KES", "Nyanza", "src", "", "", "supply", "", "", "", "", "", "", 0, "", True),
    ]
    matcher = Matcher(items, [], MatchingWeights(78, 65, 88, 4, 8, 6, 5, 18))
    line = BOQLine(sheet_name="Concrete", row_number=6, description="Mass concrete class 15", unit="m2", inferred_section="Concrete")
    result = matcher.match(line, "Nyanza")
    assert result.review_flag is True
    assert any("unit mismatch" in flag for flag in result.commercial_review_flags)

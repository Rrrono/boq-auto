from src.commercial import resolve_regional_factor, summarize_quote
from src.models import CommercialTerms, MatchResult, BOQLine, RegionalAdjustment


def test_resolve_regional_factor_prefers_specific_section() -> None:
    adjustments = [
        RegionalAdjustment(region="Nyanza", section="*", factor=1.02, notes="general"),
        RegionalAdjustment(region="Nyanza", section="Earthworks", factor=1.05, notes="earthworks"),
    ]
    factor, notes = resolve_regional_factor(adjustments, "Nyanza", "Earthworks")
    assert factor == 1.05
    assert notes == "earthworks"


def test_summarize_quote_applies_markups() -> None:
    result = MatchResult(
        boq_line=BOQLine(sheet_name="Earthworks", row_number=4, description="Excavation", quantity=10),
        decision="matched",
        rate=100.0,
        section_used="Earthworks",
    )
    summary = summarize_quote([result], CommercialTerms(overhead_pct=10, profit_pct=5, risk_pct=2, vat_pct=16))
    assert summary.matched_items == 1
    assert summary.flagged_items == 0
    assert summary.subtotal == 1000.0
    assert summary.overhead_amount == 100.0
    assert summary.profit_amount == 50.0
    assert summary.risk_amount == 20.0
    assert summary.vat_amount == 187.2
    assert summary.grand_total == 1357.2

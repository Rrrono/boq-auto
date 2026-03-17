"""Commercial quotation helpers."""

from __future__ import annotations

from collections import defaultdict

from .models import CommercialTerms, MatchResult, QuotationSummary, RegionalAdjustment, SectionSummary


def parse_float(value: str | None, default: float = 0.0) -> float:
    """Parse config or control float values safely."""
    if value in (None, ""):
        return default
    try:
        return float(str(value).strip())
    except ValueError:
        return default


def resolve_commercial_terms(config, controls: dict[str, str]) -> CommercialTerms:
    """Resolve commercial markups from config first, then database controls."""
    return CommercialTerms(
        overhead_pct=float(config.get("commercial.overheads_pct", parse_float(controls.get("overheads_pct"), 0.0))),
        profit_pct=float(config.get("commercial.profit_pct", parse_float(controls.get("profit_pct"), 0.0))),
        risk_pct=float(config.get("commercial.risk_pct", parse_float(controls.get("risk_pct"), 0.0))),
        vat_pct=float(config.get("commercial.vat_pct", parse_float(controls.get("vat_pct"), 16.0))),
        default_approval_status=str(
            config.get(
                "commercial.default_approval_status",
                controls.get("default_approval_status", "Pending Commercial Review"),
            )
        ),
    )


def resolve_regional_factor(
    adjustments: list[RegionalAdjustment],
    region: str,
    section: str,
) -> tuple[float, str]:
    """Find the most specific regional adjustment factor."""
    region_lower = region.lower()
    section_lower = section.lower()
    for adjustment in adjustments:
        if not adjustment.active:
            continue
        if adjustment.region.lower() == region_lower and adjustment.section.lower() == section_lower:
            return adjustment.factor, adjustment.notes
    for adjustment in adjustments:
        if not adjustment.active:
            continue
        if adjustment.region.lower() == region_lower and adjustment.section.strip() in {"", "*"}:
            return adjustment.factor, adjustment.notes
    return 1.0, ""


def summarize_quote(results: list[MatchResult], terms: CommercialTerms) -> QuotationSummary:
    """Build commercial totals for the quotation output."""
    totals: dict[str, float] = defaultdict(float)
    review_flags = 0
    matched_items = 0
    currency = "KES"
    for result in results:
        if result.rate is None or result.decision != "matched":
            if result.review_flag:
                review_flags += 1
            continue
        matched_items += 1
        quantity = result.boq_line.quantity or 0.0
        amount = quantity * result.rate
        section = result.section_used or result.boq_line.inferred_section or result.boq_line.sheet_name
        totals[section] += amount
        if result.source:
            currency = currency or "KES"
        if result.review_flag or result.commercial_review_flags:
            review_flags += 1

    section_totals = [SectionSummary(section=section, subtotal=round(value, 2)) for section, value in sorted(totals.items())]
    subtotal = round(sum(item.subtotal for item in section_totals), 2)
    overhead_amount = round(subtotal * terms.overhead_pct / 100, 2)
    profit_amount = round(subtotal * terms.profit_pct / 100, 2)
    risk_amount = round(subtotal * terms.risk_pct / 100, 2)
    pre_vat_total = round(subtotal + overhead_amount + profit_amount + risk_amount, 2)
    vat_amount = round(pre_vat_total * terms.vat_pct / 100, 2)
    grand_total = round(pre_vat_total + vat_amount, 2)
    bid_ready = review_flags == 0 and subtotal > 0
    reason = "Ready for issue" if bid_ready else "Human review required before issue"
    return QuotationSummary(
        section_totals=section_totals,
        currency=currency,
        subtotal=subtotal,
        overhead_amount=overhead_amount,
        profit_amount=profit_amount,
        risk_amount=risk_amount,
        pre_vat_total=pre_vat_total,
        vat_amount=vat_amount,
        grand_total=grand_total,
        matched_items=matched_items,
        flagged_items=review_flags,
        bid_ready=bid_ready,
        bid_ready_reason=reason,
    )

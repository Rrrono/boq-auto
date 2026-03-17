"""Excel workbook writing for priced BOQs and suggestions."""

from __future__ import annotations

from pathlib import Path

from openpyxl import load_workbook

from .models import CommercialTerms, MatchResult, QuotationSummary, SheetData, TextListEntry
from .utils import ensure_parent


class WorkbookWriter:
    """Write priced BOQ output without disturbing the original layout more than necessary."""

    def write(
        self,
        source_workbook: str,
        output_workbook: str,
        sheets: list[SheetData],
        results: list[MatchResult],
        quotation_summary: QuotationSummary,
        assumptions: list[TextListEntry],
        exclusions: list[TextListEntry],
        commercial_terms: CommercialTerms,
        apply_rates: bool,
        write_amount_formulas: bool,
    ) -> Path:
        """Write rates and suggestions into a copied workbook."""
        ensure_parent(Path(output_workbook))
        workbook = load_workbook(source_workbook)
        result_map = {(result.boq_line.sheet_name, result.boq_line.row_number): result for result in results}

        self._apply_pricing_to_boq(workbook, sheets, result_map, apply_rates, write_amount_formulas)
        self._reset_output_sheets(workbook)
        self._write_match_suggestions(workbook, results)
        self._write_quotation_summary(workbook, quotation_summary, commercial_terms)
        self._write_text_list_sheet(workbook, "Assumptions", "Assumption", assumptions)
        self._write_text_list_sheet(workbook, "Exclusions", "Exclusion", exclusions)
        self._write_basis_of_rates(workbook, results)
        self._write_commercial_review(workbook, results)

        workbook.save(output_workbook)
        return Path(output_workbook)

    def _apply_pricing_to_boq(self, workbook, sheets, result_map, apply_rates: bool, write_amount_formulas: bool) -> None:
        for sheet in sheets:
            worksheet = workbook[sheet.sheet_name]
            for row in sheet.rows:
                result = result_map.get((sheet.sheet_name, row.row_number))
                if not result or result.decision != "matched" or row.is_summary_row:
                    continue
                if apply_rates and sheet.columns.rate_col and result.rate is not None:
                    worksheet.cell(row.row_number, sheet.columns.rate_col).value = result.rate
                if (
                    apply_rates
                    and write_amount_formulas
                    and sheet.columns.amount_col
                    and sheet.columns.quantity_col
                    and sheet.columns.rate_col
                ):
                    qty_ref = worksheet.cell(row.row_number, sheet.columns.quantity_col).coordinate
                    rate_ref = worksheet.cell(row.row_number, sheet.columns.rate_col).coordinate
                    amount_cell = worksheet.cell(row.row_number, sheet.columns.amount_col)
                    if amount_cell.data_type != "f" or not amount_cell.value:
                        amount_cell.value = f"={qty_ref}*{rate_ref}"

    @staticmethod
    def _reset_output_sheets(workbook) -> None:
        for extra_sheet in [
            "Match Suggestions",
            "Quotation Summary",
            "Assumptions",
            "Exclusions",
            "Basis of Rates",
            "Commercial Review",
        ]:
            if extra_sheet in workbook.sheetnames:
                del workbook[extra_sheet]

    @staticmethod
    def _write_match_suggestions(workbook, results: list[MatchResult]) -> None:
        suggestions = workbook.create_sheet("Match Suggestions")
        suggestions.append(
            [
                "sheet_name", "row_number", "boq_description", "boq_unit", "boq_quantity", "decision",
                "matched_item_code", "matched_description", "matched_unit", "base_rate", "rate",
                "confidence_score", "review_flag", "section_used", "source", "region_used", "built_up",
                "basis_of_rate", "approval_status", "commercial_review_flags", "regional_factor",
                "alternate_options", "rationale",
            ]
        )
        for result in results:
            line = result.boq_line
            suggestions.append(
                [
                    line.sheet_name, line.row_number, line.description, line.unit, line.quantity, result.decision,
                    result.matched_item_code, result.matched_description, result.matched_unit, result.base_rate,
                    result.rate, result.confidence_score, "YES" if result.review_flag else "NO", result.section_used,
                    result.source, result.region_used, "YES" if result.built_up else "NO", result.basis_of_rate,
                    result.approval_status, "; ".join(result.commercial_review_flags), result.regional_factor,
                    " || ".join(result.alternate_options), "; ".join(result.rationale),
                ]
            )

    @staticmethod
    def _write_quotation_summary(workbook, quotation_summary: QuotationSummary, commercial_terms: CommercialTerms) -> None:
        summary = workbook.create_sheet("Quotation Summary")
        summary.append(["Field", "Value"])
        summary.append(["Currency", quotation_summary.currency])
        summary.append(["Bid Ready Status", "YES" if quotation_summary.bid_ready else "NO"])
        summary.append(["Bid Ready Note", quotation_summary.bid_ready_reason])
        summary.append(["Matched Items", quotation_summary.matched_items])
        summary.append(["Flagged Items", quotation_summary.flagged_items])
        summary.append(["Overheads %", commercial_terms.overhead_pct])
        summary.append(["Profit %", commercial_terms.profit_pct])
        summary.append(["Risk %", commercial_terms.risk_pct])
        summary.append(["VAT %", commercial_terms.vat_pct])
        summary.append(["", ""])
        summary.append(["Section", "Subtotal"])
        for section_total in quotation_summary.section_totals:
            summary.append([section_total.section, section_total.subtotal])
        summary.append(["Subtotal", quotation_summary.subtotal])
        summary.append(["Overheads", quotation_summary.overhead_amount])
        summary.append(["Profit", quotation_summary.profit_amount])
        summary.append(["Risk", quotation_summary.risk_amount])
        summary.append(["Pre-VAT Total", quotation_summary.pre_vat_total])
        summary.append(["VAT", quotation_summary.vat_amount])
        summary.append(["Grand Total", quotation_summary.grand_total])

    @staticmethod
    def _write_text_list_sheet(workbook, title: str, label: str, entries: list[TextListEntry]) -> None:
        sheet = workbook.create_sheet(title)
        sheet.append(["Category", label])
        for entry in entries:
            sheet.append([entry.category, entry.text])

    @staticmethod
    def _write_basis_of_rates(workbook, results: list[MatchResult]) -> None:
        basis_sheet = workbook.create_sheet("Basis of Rates")
        basis_sheet.append(
            [
                "sheet_name", "row_number", "boq_description", "matched_item_code", "matched_description",
                "source", "basis_of_rate", "region_used", "regional_factor",
            ]
        )
        for result in results:
            basis_sheet.append(
                [
                    result.boq_line.sheet_name, result.boq_line.row_number, result.boq_line.description,
                    result.matched_item_code, result.matched_description, result.source, result.basis_of_rate,
                    result.region_used, result.regional_factor,
                ]
            )

    @staticmethod
    def _write_commercial_review(workbook, results: list[MatchResult]) -> None:
        review_sheet = workbook.create_sheet("Commercial Review")
        review_sheet.append(
            [
                "sheet_name", "row_number", "boq_description", "decision", "approval_status",
                "commercial_review_flags", "alternate_options",
            ]
        )
        for result in results:
            if not result.commercial_review_flags and not result.review_flag:
                continue
            review_sheet.append(
                [
                    result.boq_line.sheet_name, result.boq_line.row_number, result.boq_line.description,
                    result.decision, result.approval_status, "; ".join(result.commercial_review_flags),
                    " || ".join(result.alternate_options),
                ]
            )

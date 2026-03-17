from openpyxl import Workbook, load_workbook

from src.ingestion import (
    ALIASES_HEADERS,
    CANDIDATE_MATCH_HEADERS,
    RATE_LIBRARY_HEADERS,
    REVIEW_LOG_HEADERS,
    generate_review_report,
    merge_reviewed_candidates,
    promote_approved_candidates,
)


def _make_review_db(path) -> None:
    workbook = Workbook()
    default = workbook.active
    workbook.remove(default)

    rate_sheet = workbook.create_sheet("RateLibrary")
    rate_sheet.append(RATE_LIBRARY_HEADERS)
    rate_sheet.append(
        ["PL001", "15 tonne tipper lorry", "15 ton tipper lorry", "Dayworks", "Plant", "day", 18500, "KES", "Nyanza", "QS", "Plant", "12", "hire", "", "transport", "", "", "", "", 4, "", True]
    )

    aliases = workbook.create_sheet("Aliases")
    aliases.append(ALIASES_HEADERS)

    review_log = workbook.create_sheet("ReviewLog")
    review_log.append(REVIEW_LOG_HEADERS)

    candidates = workbook.create_sheet("CandidateMatches")
    candidates.append(CANDIDATE_MATCH_HEADERS)
    candidates.append(
        [
            "2026-03-17T09:00:00", "batch-1", "review.csv", "Sheet1", "RateLibrary", "PL001X",
            "Tipper truck hire", "tipper truck hire", "Dayworks", "Plant", "day", 17800, "KES", "Nyanza",
            "Estimator Review", "44", "Reviewed daywork comparison", "", "transport", "", "tipper lorry", "tipper",
            "", 72, "close duplicate requires review", True, "duplicate normalized description + unit", "PL001",
            "approved", "Senior QS", "2026-03-17T10:15:00", "accept", "aliases",
            "", "", "", "tipper lorry", "Dayworks", 88, "Prefer alias", "not_promoted", "",
        ]
    )
    workbook.save(path)


def test_generate_review_report_creates_candidate_review_sheet(tmp_path) -> None:
    db_path = tmp_path / "review_db.xlsx"
    _make_review_db(db_path)
    summary = generate_review_report(str(db_path))
    workbook = load_workbook(db_path)
    assert "Candidate Review" in workbook.sheetnames
    assert summary.report_rows == 1


def test_merge_reviewed_and_promote_alias(tmp_path) -> None:
    db_path = tmp_path / "review_db.xlsx"
    json_path = tmp_path / "training.json"
    _make_review_db(db_path)
    generate_review_report(str(db_path))

    workbook = load_workbook(db_path)
    review_sheet = workbook["Candidate Review"]
    headers = [cell.value for cell in review_sheet[1]]
    positions = {header: idx + 1 for idx, header in enumerate(headers)}
    review_sheet.cell(2, positions["reviewer_status"]).value = "approved"
    review_sheet.cell(2, positions["promote_target"]).value = "aliases"
    review_sheet.cell(2, positions["approved_canonical_term"]).value = "tipper lorry"
    review_sheet.cell(2, positions["confidence_override"]).value = 91
    workbook.save(db_path)

    merge_summary = merge_reviewed_candidates(str(db_path), "Senior QS")
    promote_summary = promote_approved_candidates(str(db_path), str(json_path))

    workbook = load_workbook(db_path)
    alias_sheet = workbook["Aliases"]
    assert merge_summary.reviewed == 1
    assert promote_summary.promoted == 1
    assert alias_sheet.max_row == 2
    assert json_path.exists()

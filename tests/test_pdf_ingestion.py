from pathlib import Path

from src.models import AppConfig
from src.pdf_classifier import is_scanned_pdf
from src.pdf_ingestion import extract_text_from_pdf
from src.tender_reader import read_tender_document


def test_is_scanned_pdf_flags_sparse_text() -> None:
    assert is_scanned_pdf("")
    assert is_scanned_pdf("   \n\t  ")
    assert not is_scanned_pdf("Tender requirements and preliminaries section with enough readable text to exceed the scan threshold.")


def test_extract_text_from_pdf_uses_ocr_fallback_when_direct_text_is_short(tmp_path, monkeypatch) -> None:
    pdf_path = tmp_path / "scan.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    calls = {"ocr": 0}

    monkeypatch.setattr("src.pdf_ingestion._extract_direct_text", lambda path: " ")

    def fake_ocr(path: Path) -> str:
        calls["ocr"] += 1
        return "Scanned tender requirements\nBill of quantities to follow"

    monkeypatch.setattr("src.pdf_ingestion._extract_with_ocr", fake_ocr)

    text = extract_text_from_pdf(str(pdf_path), config=AppConfig(data={}))

    assert calls["ocr"] == 1
    assert text
    assert "Scanned tender requirements" in text


def test_tender_reader_accepts_pdf_input_without_crashing(tmp_path, monkeypatch) -> None:
    pdf_path = tmp_path / "tender.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    monkeypatch.setattr(
        "src.tender_reader.extract_text_from_pdf",
        lambda path, config=None, logger=None: "Tender for proposed works\nSite visit is mandatory",
    )

    document = read_tender_document(pdf_path, config=AppConfig(data={}))

    assert document.document_type == "pdf"
    assert document.lines
    assert "Site visit is mandatory" in document.text

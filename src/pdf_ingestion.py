"""PDF tender ingestion with direct extraction and OCR fallback."""

from __future__ import annotations

import logging
from pathlib import Path

try:
    import fitz
except ImportError:  # pragma: no cover - dependency presence is environment-specific
    fitz = None

try:
    from PIL import Image
except ImportError:  # pragma: no cover - dependency presence is environment-specific
    Image = None

try:
    import pytesseract
except ImportError:  # pragma: no cover - dependency presence is environment-specific
    pytesseract = None

from .models import AppConfig
from .pdf_classifier import is_scanned_pdf


def _normalize_text(text: str) -> str:
    lines = []
    for raw_line in text.replace("\r", "\n").splitlines():
        cleaned = " ".join(raw_line.split()).strip()
        if cleaned:
            lines.append(cleaned)
    return "\n".join(lines)


def _apply_tesseract_path(config: AppConfig | None) -> None:
    if pytesseract is None or config is None:
        return
    tesseract_path = str(config.get("tesseract_path", "")).strip()
    if tesseract_path:
        pytesseract.pytesseract.tesseract_cmd = tesseract_path


def _require_direct_extraction_dependencies() -> None:
    if fitz is None:
        raise RuntimeError("PDF ingestion dependency is missing: PyMuPDF")


def _require_ocr_dependencies() -> None:
    missing: list[str] = []
    if pytesseract is None:
        missing.append("pytesseract")
    if Image is None:
        missing.append("Pillow")
    if fitz is None:
        missing.append("PyMuPDF")
    if missing:
        raise RuntimeError(f"PDF OCR dependencies are missing: {', '.join(missing)}")


def _extract_direct_text(path: Path) -> str:
    _require_direct_extraction_dependencies()
    chunks: list[str] = []
    with fitz.open(path) as document:
        for page in document:
            chunks.append(page.get_text("text"))
    return _normalize_text("\n".join(chunks))


def _pixmap_to_image(pixmap) -> Image.Image:
    mode = "RGB"
    if getattr(pixmap, "alpha", 0):
        mode = "RGBA"
    return Image.frombytes(mode, [pixmap.width, pixmap.height], pixmap.samples)


def _extract_with_ocr(path: Path) -> str:
    _require_ocr_dependencies()
    chunks: list[str] = []
    with fitz.open(path) as document:
        for page in document:
            pixmap = page.get_pixmap(alpha=False)
            image = _pixmap_to_image(pixmap)
            chunks.append(pytesseract.image_to_string(image))
    return _normalize_text("\n".join(chunks))


def extract_text_from_pdf(path: str, config: AppConfig | None = None, logger: logging.Logger | None = None) -> str:
    """Extract text from a PDF using direct text extraction, then OCR when needed."""

    pdf_path = Path(path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF input not found: {pdf_path}")

    _apply_tesseract_path(config)

    if logger:
        logger.info("PDF detected: attempting direct extraction")
    text = _extract_direct_text(pdf_path)
    if not is_scanned_pdf(text):
        return text

    if logger:
        logger.info("Direct extraction insufficient, using OCR fallback")
    try:
        ocr_text = _extract_with_ocr(pdf_path)
    except Exception as exc:
        raise RuntimeError(
            "OCR fallback failed. Confirm Tesseract is installed and set config/default.yaml `tesseract_path` when needed."
        ) from exc
    if logger:
        logger.info("OCR completed: %s characters extracted", len(ocr_text))
    return ocr_text

"""Heuristics for deciding when a PDF likely needs OCR."""

from __future__ import annotations


MIN_DIRECT_TEXT_LENGTH = 80
MIN_NON_WHITESPACE_CHARS = 40


def is_scanned_pdf(text: str) -> bool:
    """Return True when extracted PDF text is too sparse to trust as direct text."""

    if not text:
        return True

    stripped = text.strip()
    if not stripped:
        return True

    non_whitespace = sum(1 for char in text if not char.isspace())
    return len(stripped) < MIN_DIRECT_TEXT_LENGTH or non_whitespace < MIN_NON_WHITESPACE_CHARS

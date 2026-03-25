"""Heuristics for deciding when a PDF likely needs OCR."""

from __future__ import annotations


MIN_DIRECT_TEXT_LENGTH = 80
MIN_NON_WHITESPACE_CHARS = 40
MIN_UNIQUE_LINES = 3
MAX_MOST_COMMON_LINE_SHARE = 0.6


def is_scanned_pdf(text: str) -> bool:
    """Return True when extracted PDF text is too sparse to trust as direct text."""

    if not text:
        return True

    stripped = text.strip()
    if not stripped:
        return True

    non_whitespace = sum(1 for char in text if not char.isspace())
    if len(stripped) < MIN_DIRECT_TEXT_LENGTH or non_whitespace < MIN_NON_WHITESPACE_CHARS:
        return True

    lines = [" ".join(line.split()) for line in text.splitlines() if line.strip()]
    if not lines:
        return True
    if len(lines) < 5:
        return False
    unique_lines = {line for line in lines}
    if len(unique_lines) < MIN_UNIQUE_LINES:
        return True

    most_common_line_count = max(lines.count(line) for line in unique_lines)
    return (most_common_line_count / len(lines)) >= MAX_MOST_COMMON_LINE_SHARE

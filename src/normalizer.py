"""Text normalization utilities for BOQ matching."""

from __future__ import annotations

import re
import unicodedata

STOP_WORDS = {"complete", "including", "with", "and", "of", "the", "type"}

UNIT_SYNONYMS = {
    "m3": "m3",
    "m^3": "m3",
    "cm": "m3",
    "m2": "m2",
    "sm": "m2",
    "sqm": "m2",
    "sqm.": "m2",
    "sq.m": "m2",
    "sqmeter": "m2",
    "sqmtr": "m2",
    "kw": "kw",
    "kilowatt": "kw",
    "cfm": "cfm",
    "nr": "nr",
    "no": "nr",
    "nos": "nr",
    "pcs": "nr",
    "item": "item",
    "sum": "sum",
    "ls": "sum",
    "tonne": "ton",
    "tonnes": "ton",
    "ton": "ton",
}


def normalize_text(text: str) -> str:
    """Normalize free text for fuzzy matching."""
    if not text:
        return ""

    value = unicodedata.normalize("NFKD", str(text))
    value = value.encode("ascii", "ignore").decode("ascii")
    value = value.lower()
    value = value.replace("m^3", "m3").replace("m^2", "m2")
    value = re.sub(r"(\d)\s*[^a-z0-9./ ]+\s*(\d)", r"\1 \2", value)
    value = re.sub(r"\b(c\.?f\.?m)\b", "cfm", value)
    value = re.sub(r"\btonnes?\b", "ton", value)
    value = re.sub(r"\blitres?\b", "litre", value)
    value = re.sub(r"\bhrs?\b", "hr", value)
    value = re.sub(r"[^a-z0-9./ ]+", " ", value)
    parts = [token for token in value.split() if token not in STOP_WORDS]
    return " ".join(parts).strip()


def normalize_unit(unit: str) -> str:
    """Normalize units into a compact comparable form."""
    normalized = normalize_text(unit).replace(" ", "")
    return UNIT_SYNONYMS.get(normalized, normalized)

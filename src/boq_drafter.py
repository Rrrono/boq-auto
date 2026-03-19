"""Draft BOQ suggestion generation from tender analysis outputs."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import re

from .models import AppConfig
from .normalizer import normalize_text
from .tender_models import DraftBOQSuggestion, ScopeSection, TenderDocument, TenderSourceLine


def _clean_line_text(text: str) -> str:
    return text.strip().lstrip("-").strip().rstrip(":").strip()


@dataclass(slots=True)
class _DraftCandidate:
    section: str
    description: str
    unit: str
    source_references: list[str]
    source_basis_parts: list[str]
    source_excerpt_parts: list[str]
    notes_parts: list[str]
    confidence: float


WORK_ITEM_PATTERNS = [
    ("excavation", ("excavate", "excavation", "reduce levels", "cut to spoil"), "Excavation to reduce levels and cart away surplus material", "m3"),
    ("foundation_excavation", ("excavate foundations", "excavation for foundations", "trench excavation"), "Excavation for foundations", "m3"),
    ("disposal", ("cart away", "dispose", "disposal", "surplus material", "unsuitable material"), "Excavation and disposal of unsuitable material", "m3"),
    ("filling", ("fill", "filling", "backfill", "selected material"), "Fill with approved selected material", "m3"),
    ("compaction", ("compact", "compaction", "specified density", "subgrade"), "Compaction of fill to specified density", "m2"),
    ("benching", ("benching", "widening", "subgrade preparation"), "Benching for widening and subgrade preparation", ""),
    ("concrete", ("concrete", "blinding", "strip foundations", "floor slab", "apron"), "In-situ concrete works", "m3"),
    ("reinforcement", ("reinforcement", "rebar", "bar bending"), "Reinforcement to concrete works", "kg"),
    ("formwork", ("formwork", "shuttering"), "Formwork to concrete surfaces", "m2"),
    ("plaster", ("plaster", "plastering"), "Plaster to internal and external surfaces", "m2"),
    ("paint", ("paint", "painting"), "Painting and decorating", "m2"),
    ("screed", ("screed", "floor screed"), "Floor screed finish", "m2"),
    ("tiling", ("tile", "tiling"), "Wall and floor tiling", "m2"),
    ("manholes", ("manhole", "inspection chamber"), "Construct manholes complete", "nr"),
    ("pipe_laying", ("pipe", "pipe laying", "upvc", "hdpe"), "Lay and joint pipes", "m"),
    ("drainage", ("stormwater", "drainage", "outfall", "culvert"), "Drainage installation complete", "m"),
    ("paving", ("paving", "cabro", "block paving"), "Paving to external works", "m2"),
    ("fencing", ("fence", "fencing", "chainlink"), "Chainlink fencing complete", "m"),
    ("electrical", ("electrical", "lighting", "power", "cabling", "socket"), "Electrical installation complete", ""),
]
INSTRUCTION_PATTERNS = (
    "refer to section",
    "see section",
    "in accordance with",
    "comply with",
    "submit",
    "provide for approval",
    "shall be approved",
)
DEFINITION_PATTERNS = ("means", "shall mean", "is defined as", "definition")
CONTINUATION_PREFIXES = ("and ", "including ", "with ", "to ", "of ", "for ", "where ", "as ", "in ", "on ", "or ")
WORK_VERBS = {
    "excavate", "excavation", "fill", "backfill", "compact", "compaction", "dispose", "disposal",
    "construct", "lay", "install", "cast", "form", "reinforce", "paint",
    "plaster", "screed", "tile", "pave", "bench", "prepare",
}


class BOQDrafter:
    """Generate review-first draft BOQ suggestions from tender text."""

    def __init__(self, config: AppConfig, logger: logging.Logger | None = None) -> None:
        self.config = config
        self.logger = logger
        raw_units: dict[str, str] = config.get("tender_analysis.draft_units", {})
        self.config_units = {
            normalize_text(key).replace(" ", "_"): str(value)
            for key, value in raw_units.items()
        }

    def build_suggestions(self, document: TenderDocument, scope_sections: list[ScopeSection]) -> list[DraftBOQSuggestion]:
        suggestions: list[DraftBOQSuggestion] = []

        for section in scope_sections:
            section_lines = self._collect_section_lines(document, section)
            merged_lines = self._merge_continuations(section_lines)
            candidates = self._build_candidates(section, merged_lines)
            if not candidates:
                suggestions.append(self._section_placeholder(section))
                continue
            suggestions.extend(self._consolidate_candidates(candidates))

        if self.logger:
            self.logger.info("Built %s draft BOQ suggestion(s).", len(suggestions))
        return suggestions

    def _collect_section_lines(self, document: TenderDocument, section: ScopeSection) -> list[TenderSourceLine]:
        section_refs = set(section.source_references)
        keywords = [keyword.lower() for keyword in section.matched_keywords]
        lines: list[TenderSourceLine] = []
        previous_included = False
        for index, line in enumerate(document.lines):
            normalized = line.text.lower()
            direct_match = line.source_reference in section_refs
            keyword_match = any(keyword in normalized for keyword in keywords if keyword)
            continuation_match = index > 0 and previous_included and self._is_continuation_line(line.text)
            include_line = direct_match or keyword_match or continuation_match
            if include_line and self._is_definition_text(line.text):
                previous_included = False
                continue
            if include_line:
                lines.append(line)
            previous_included = include_line
        return lines

    def _merge_continuations(self, lines: list[TenderSourceLine]) -> list[tuple[str, str]]:
        merged: list[tuple[str, str]] = []
        current_text = ""
        current_refs: list[str] = []
        for line in lines:
            text = _clean_line_text(line.text)
            if not text:
                continue
            if current_text and self._should_merge(current_text, text):
                joiner = " " if current_text.endswith((",", ";")) or self._is_continuation_line(text) else ". "
                current_text = f"{current_text.rstrip('.')} {text}".strip() if joiner == " " else f"{current_text}{joiner}{text}"
                current_refs.append(line.source_reference)
                continue
            if current_text:
                merged.append((", ".join(dict.fromkeys(current_refs)), current_text))
            current_text = text
            current_refs = [line.source_reference]
        if current_text:
            merged.append((", ".join(dict.fromkeys(current_refs)), current_text))
        return merged

    def _build_candidates(self, section: ScopeSection, merged_lines: list[tuple[str, str]]) -> list[_DraftCandidate]:
        candidates: list[_DraftCandidate] = []
        for source_reference, text in merged_lines:
            if self._should_filter_clause(text):
                continue
            synthesized = self._synthesize_descriptions(section.section_name, text)
            if not synthesized:
                if self._looks_like_measurable_work(text):
                    synthesized = [(self._fallback_description(text), "", 58.0, "Measured work wording detected but item wording is still broad.")]
                else:
                    continue
            for description, unit, confidence, note in synthesized:
                candidates.append(
                    _DraftCandidate(
                        section=section.section_name,
                        description=description,
                        unit=self._suggest_unit(section.section_name, description, unit, text),
                        source_references=[source_reference],
                        source_basis_parts=[f"Tender text matched via {', '.join(section.matched_keywords)}"],
                        source_excerpt_parts=[text],
                        notes_parts=[
                            "Draft BOQ suggestion only. Quantity must be measured or confirmed.",
                            note,
                        ],
                        confidence=max(55.0, min(max(section.confidence - 6.0, confidence), 86.0)),
                    )
                )
        return candidates

    def _consolidate_candidates(self, candidates: list[_DraftCandidate]) -> list[DraftBOQSuggestion]:
        consolidated: dict[tuple[str, str], _DraftCandidate] = {}
        for candidate in candidates:
            signature = (candidate.section, normalize_text(candidate.description))
            existing = consolidated.get(signature)
            if existing is None:
                consolidated[signature] = candidate
                continue
            existing.source_references.extend(candidate.source_references)
            existing.source_basis_parts.extend(candidate.source_basis_parts)
            existing.source_excerpt_parts.extend(candidate.source_excerpt_parts)
            existing.notes_parts.extend(candidate.notes_parts)
            existing.confidence = min(max(existing.confidence, candidate.confidence) + 2.0, 90.0)
            if not existing.unit and candidate.unit:
                existing.unit = candidate.unit

        suggestions: list[DraftBOQSuggestion] = []
        for candidate in consolidated.values():
            notes = "; ".join(dict.fromkeys(part for part in candidate.notes_parts if part))
            if len(candidate.source_excerpt_parts) > 1:
                notes = f"{notes}; Consolidated from multiple related tender clauses."
            suggestions.append(
                DraftBOQSuggestion(
                    section=candidate.section,
                    description=candidate.description,
                    unit=candidate.unit,
                    quantity_placeholder="TBD",
                    rate_placeholder="Rate to be built/priced",
                    amount_placeholder="Derived after measurement",
                    source_basis=" | ".join(dict.fromkeys(candidate.source_basis_parts)),
                    source_reference=", ".join(dict.fromkeys(candidate.source_references)),
                    source_excerpt=" | ".join(dict.fromkeys(candidate.source_excerpt_parts))[:500],
                    confidence=round(candidate.confidence, 1),
                    notes=notes,
                )
            )
        return suggestions

    def _section_placeholder(self, section: ScopeSection) -> DraftBOQSuggestion:
        return DraftBOQSuggestion(
            section=section.section_name,
            description=f"Insert BOQ line items for {section.section_name.lower()} based on tender text.",
            unit=self._suggest_unit(section.section_name, section.section_name, "", section.section_name),
            quantity_placeholder="TBD",
            rate_placeholder="Rate to be built/priced",
            amount_placeholder="Derived after measurement",
            source_basis=f"Scope section inferred from keywords: {', '.join(section.matched_keywords)}",
            source_reference=", ".join(section.source_references),
            source_excerpt=section.notes,
            confidence=max(50.0, min(section.confidence - 5.0, 80.0)),
            notes="Section-level placeholder because no clear line-item wording was found.",
        )

    def _suggest_unit(self, section_name: str, description: str, pattern_unit: str, source_text: str) -> str:
        lowered = f"{description} {source_text}".lower()
        normalized_section = normalize_text(section_name).replace(" ", "_")
        if normalized_section in self.config_units:
            return str(self.config_units[normalized_section])
        if pattern_unit:
            return pattern_unit
        if any(token in lowered for token in {"excavation", "concrete", "backfill", "fill", "disposal"}) and any(
            token in lowered for token in {"m3", "cubic", "volume", "density", "bulk"}
        ):
            return "m3"
        if any(token in lowered for token in {"paint", "plaster", "tiling", "screed", "paving", "compaction"}) and any(
            token in lowered for token in {"m2", "square", "surface", "area"}
        ):
            return "m2"
        if any(token in lowered for token in {"fence", "pipe", "cabling"}) and any(
            token in lowered for token in {"m", "metre", "linear", "run"}
        ):
            return "m"
        if any(token in lowered for token in {"manhole", "light", "pump", "fitting"}) and any(
            token in lowered for token in {"nr", "number", "each", "no."}
        ):
            return "nr"
        return ""

    def _is_continuation_line(self, text: str) -> bool:
        stripped = text.strip()
        if not stripped:
            return False
        lowered = stripped.lower()
        return (
            stripped[0].islower()
            or lowered.startswith(CONTINUATION_PREFIXES)
            or stripped.startswith(("(", ",", ";"))
            or len(stripped.split()) <= 5
        )

    def _should_merge(self, current_text: str, next_text: str) -> bool:
        if self._is_continuation_line(next_text):
            return True
        if current_text.endswith((",", ";", ":")):
            return True
        if re.match(r"^\d+(\.\d+)*$", current_text.strip()):
            return True
        return False

    def _should_filter_clause(self, text: str) -> bool:
        cleaned = _clean_line_text(text)
        lowered = cleaned.lower()
        if not cleaned or len(cleaned.split()) < 3:
            return True
        if re.match(r"^(section|clause)\s+\d+[a-z0-9.\-\u2013]*", lowered):
            return True
        if cleaned.isupper() and len(cleaned.split()) <= 8:
            return True
        if re.match(r"^\d+(\.\d+)*\s*$", lowered):
            return True
        if self._is_definition_text(cleaned):
            return True
        if any(pattern in lowered for pattern in INSTRUCTION_PATTERNS) and not self._looks_like_measurable_work(cleaned):
            return True
        if lowered.startswith(("definition", "interpretation")):
            return True
        if re.match(r"^[a-z]?[).\-]\s*", lowered) and not self._looks_like_measurable_work(cleaned):
            return True
        if "refer to" in lowered and not self._looks_like_measurable_work(cleaned):
            return True
        return False

    def _is_definition_text(self, text: str) -> bool:
        lowered = _clean_line_text(text).lower()
        if any(pattern in lowered for pattern in DEFINITION_PATTERNS):
            return True
        return lowered.startswith(("definition of", "definitions of"))

    def _looks_like_measurable_work(self, text: str) -> bool:
        lowered = text.lower()
        if any(phrase in lowered for _, phrases, _, _ in WORK_ITEM_PATTERNS for phrase in phrases):
            return True
        return any(f" {verb}" in f" {lowered}" for verb in WORK_VERBS)

    def _synthesize_descriptions(self, section_name: str, text: str) -> list[tuple[str, str, float, str]]:
        lowered = text.lower()
        suggestions: list[tuple[str, str, float, str]] = []
        seen: set[str] = set()
        matched_keys = {
            key
            for key, phrases, _, _ in WORK_ITEM_PATTERNS
            if any(phrase in lowered for phrase in phrases)
        }
        for key, phrases, description, unit in WORK_ITEM_PATTERNS:
            if key == "excavation" and "foundation_excavation" in matched_keys:
                continue
            if not any(phrase in lowered for phrase in phrases):
                continue
            normalized = normalize_text(description)
            if normalized in seen:
                continue
            seen.add(normalized)
            note = "Synthesized from tender clause wording for review-first BOQ drafting."
            confidence = 68.0
            if section_name.lower() in description.lower():
                confidence += 2.0
            suggestions.append((description, unit, confidence, note))

        if suggestions:
            return suggestions[:4]
        return []

    def _fallback_description(self, text: str) -> str:
        cleaned = _clean_line_text(text)
        cleaned = re.sub(r"^\d+(\.\d+)*\s*", "", cleaned)
        lowered = cleaned.lower()
        lowered = re.sub(r"\b(the contractor shall|contractor shall|shall|must|should)\b", "", lowered)
        lowered = re.sub(r"\b(all|any|where indicated|where required|as directed|as necessary)\b", "", lowered)
        lowered = " ".join(lowered.split())
        if lowered:
            lowered = lowered[0].upper() + lowered[1:]
        return lowered[:96].rstrip(" ,;:.")

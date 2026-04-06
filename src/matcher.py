"""Matching engine for BOQ descriptions against the rate library."""

from __future__ import annotations

from dataclasses import dataclass
from math import fabs
import re

from rapidfuzz import fuzz

from .aliases import apply_aliases
from .matching_engine import MatchingEngine
from .models import AliasEntry, MatchResult, RateItem, BOQLine
from .normalizer import normalize_text, normalize_unit


@dataclass(slots=True)
class MatchingWeights:
    threshold: float
    review_threshold: float
    strong_threshold: float
    region_bonus: float
    section_bonus: float
    unit_bonus: float
    alias_bonus: float
    unit_penalty: float
    attribute_bonus: float


class Matcher:
    """Perform section-aware and unit-aware fuzzy matching."""

    def __init__(
        self,
        rate_items: list[RateItem],
        aliases: list[AliasEntry],
        weights: MatchingWeights,
        matching_mode: str = "rule",
        matching_engine: MatchingEngine | None = None,
    ) -> None:
        self.rate_items = [item for item in rate_items if item.active]
        self.aliases = aliases
        self.weights = weights
        self.matching_mode = matching_mode
        self.matching_engine = matching_engine

    CATEGORY_HINTS: dict[str, tuple[str, ...]] = {
        "earthworks": ("excavat", "trench", "backfill", "fill", "cart away", "earthwork", "soil", "hardcore"),
        "concrete": ("concrete", "blinding", "reinforced", "formwork", "rebar", "vibrator", "strip footing"),
        "masonry": ("blockwork", "stone wall", "masonry", "brickwork", "walling", "mortar"),
        "electrical": ("light", "lighting", "socket", "cable", "switch", "distribution board", "electrical", "conduit"),
        "plumbing": ("pipe", "drain", "sewer", "manhole", "water supply", "sanitary", "plumbing"),
        "finishes": ("paint", "plaster", "screed", "tile", "ceiling", "finish", "render"),
        "survey": ("survey", "setting out", "beacon", "leveling", "chainage", "theodolite", "total station"),
        "lab_testing": ("test", "testing", "laboratory", "lab", "cube", "soil test", "material test"),
        "furniture_accommodation": ("furniture", "bed", "mattress", "wardrobe", "sofa", "chair", "table", "housing", "accommodation"),
        "electrical_support": ("generator", "transformer", "pole", "earthing", "lightning", "cctv", "fire alarm", "solar"),
        "dayworks": ("daywork", "hire", "plant", "excavator", "tipper", "truck", "roller", "grader"),
    }
    GENERIC_TERMS: tuple[str, ...] = (
        "general",
        "general item",
        "preliminary",
        "preliminaries",
        "provisional",
        "provisional sum",
        "contingency",
        "sundries",
        "miscellaneous",
        "other item",
        "concrete work",
        "electrical works",
        "plumbing works",
        "dayworks",
    )

    def match(self, line: BOQLine, region: str) -> MatchResult:
        """Return the best matching rate item for a BOQ line."""
        normalized_query, alias_hits = apply_aliases(line.description, self.aliases)
        line.normalized_description = normalized_query
        normalized_attributes = normalize_text(getattr(line, "spec_attributes", "") or "")
        attribute_terms = {token for token in normalized_attributes.split() if len(token) > 2}
        query_category = self._infer_category(normalized_query, line.inferred_section)
        alias_section_match = any(
            entry.section_bias and line.inferred_section and entry.section_bias.lower() == line.inferred_section.lower()
            for entry in alias_hits
        )

        external_scores: dict[str, tuple[float, list[str]]] = {}
        if self.matching_mode in {"ai", "hybrid"} and self.matching_engine is not None:
            for candidate in self.matching_engine.match(normalized_query, self.rate_items):
                item_code = getattr(candidate.item, "item_code", "")
                if item_code:
                    external_scores[str(item_code)] = (candidate.score, list(candidate.rationale))
        effective_mode = self.matching_mode
        if effective_mode == "ai" and not external_scores:
            effective_mode = "rule"
        elif effective_mode == "hybrid" and not external_scores:
            effective_mode = "rule"

        ranked: list[tuple[float, RateItem, list[str]]] = []

        for item in self.rate_items:
            description_score = fuzz.token_sort_ratio(normalized_query, item.normalized_description)
            partial_score = fuzz.partial_ratio(normalized_query, item.normalized_description)
            token_set_score = fuzz.token_set_ratio(normalized_query, item.normalized_description)
            score = (description_score * 0.45) + (partial_score * 0.20) + (token_set_score * 0.35)
            rationale = [f"text={score:.1f}", f"sort={description_score:.1f}", f"set={token_set_score:.1f}"]
            review_flags: list[str] = []
            item_category = self._infer_category(item.normalized_description, item.section)
            generic_match_flag = self._generic_match_flag(normalized_query, item)
            category_mismatch_flag = False
            section_mismatch_flag = False

            if line.inferred_section and item.section and line.inferred_section.lower() == item.section.lower():
                score += self.weights.section_bonus
                rationale.append("section-bonus")
            elif line.inferred_section and item.section:
                score -= self.weights.section_bonus * 1.15
                review_flags.append("section mismatch")
                section_mismatch_flag = True

            if region and item.region and region.lower() == item.region.lower():
                score += self.weights.region_bonus
                rationale.append("region-bonus")

            if line.unit and item.unit:
                line_unit = normalize_unit(line.unit)
                item_unit = normalize_unit(item.unit)
                if line_unit == item_unit:
                    score += self.weights.unit_bonus
                    rationale.append("unit-bonus")
                else:
                    score -= self.weights.unit_penalty * 1.25
                    rationale.append("unit-penalty")
                    review_flags.append(f"unit mismatch: boq={line_unit} library={item_unit}")
            elif not line.unit:
                review_flags.append("missing boq unit")

            if alias_hits:
                score += min(len(alias_hits), 2) * self.weights.alias_bonus
                rationale.append("alias-bonus")
            if alias_section_match:
                score += self.weights.alias_bonus
                rationale.append("alias-section-bonus")

            if attribute_terms:
                attribute_score = self._attribute_overlap(attribute_terms, item)
                if attribute_score > 0:
                    score += attribute_score * self.weights.attribute_bonus
                    rationale.append(f"attribute={attribute_score:.2f}")

            if query_category and item_category and query_category != item_category:
                category_mismatch_flag = True
                score -= max(self.weights.alias_bonus + 3.0, self.weights.section_bonus * 0.9)
                review_flags.append(f"category mismatch: boq={query_category} library={item_category}")

            if generic_match_flag:
                score -= max(6.0, self.weights.alias_bonus + 1.0)
                review_flags.append("generic candidate match")

            external_score, external_rationale = external_scores.get(item.item_code, (0.0, []))
            if effective_mode == "ai":
                if not external_score:
                    continue
                score = external_score
                rationale = list(external_rationale) or [f"ai={external_score:.1f}"]
            elif effective_mode == "hybrid" and external_score:
                score = external_score
                rationale = list(external_rationale)

            if self.matching_engine is not None and not (effective_mode in {"ai", "hybrid"} and external_score):
                learning_adjustment, learning_notes = self.matching_engine.learning_adjustment(normalized_query, item.item_code)
                score += learning_adjustment
                rationale.extend(learning_notes)

            score += item.confidence_hint
            if fabs(description_score - partial_score) > 20:
                review_flags.append("unstable text score")
            if review_flags:
                rationale.extend(review_flags)
            ranked.append((score, item, rationale, generic_match_flag, category_mismatch_flag, section_mismatch_flag))

        ranked.sort(key=lambda entry: entry[0], reverse=True)
        if not ranked:
            return MatchResult(boq_line=line, decision="unmatched", review_flag=True, rationale=["no-active-items"])

        best_score, best_item, best_rationale, generic_match_flag, category_mismatch_flag, section_mismatch_flag = ranked[0]
        alternate_options = [
            f"{item.item_code} | {item.description} | {item.unit} | {item.rate:.2f} | {score:.1f}"
            for score, item, _, _, _, _ in ranked[1:4]
            if score >= self.weights.review_threshold
        ]

        confidence_band = self._confidence_band(best_score)
        decision = "matched" if best_score >= self.weights.threshold else "review"
        unit_mismatch_forced_review = any(note.startswith("unit mismatch:") for note in best_rationale)
        suspicious_match = generic_match_flag or category_mismatch_flag or section_mismatch_flag
        if suspicious_match and best_score < self.weights.strong_threshold:
            decision = "review"
        if best_score < self.weights.review_threshold:
            decision = "unmatched"
        flag_reasons = self._flag_reasons(best_rationale, confidence_band)
        review_flag = (best_score < self.weights.strong_threshold) or unit_mismatch_forced_review or decision != "matched"
        commercial_review_flags = [note for note in best_rationale if "mismatch" in note or "missing" in note or "unstable" in note or "generic" in note]
        return MatchResult(
            boq_line=line,
            decision=decision,
            matched_item_code=best_item.item_code,
            matched_description=best_item.description,
            matched_unit=best_item.unit,
            base_rate=best_item.rate,
            rate=best_item.rate,
            confidence_score=round(best_score, 2),
            review_flag=review_flag or decision != "matched",
            section_used=best_item.section,
            source=best_item.source,
            region_used=best_item.region or region,
            basis_of_rate=best_item.basis,
            alternate_options=alternate_options,
            confidence_band=confidence_band,
            flag_reasons=flag_reasons,
            generic_match_flag=generic_match_flag,
            category_mismatch_flag=category_mismatch_flag,
            section_mismatch_flag=section_mismatch_flag,
            commercial_review_flags=commercial_review_flags,
            rationale=best_rationale,
        )

    def _infer_category(self, text: str, section: str = "") -> str:
        haystack = normalize_text(" ".join(part for part in [text, section] if part))
        if not haystack:
            return ""
        normalized_section = normalize_text(section)
        for category, terms in self.CATEGORY_HINTS.items():
            if normalized_section and category in normalized_section:
                return category
            if any(term in haystack for term in terms):
                return category
        return ""

    def _generic_match_flag(self, normalized_query: str, item: RateItem) -> bool:
        item_text = normalize_text(" ".join(part for part in [item.description, item.section, item.notes] if part))
        if not item_text:
            return False
        item_generic = any(term in item_text for term in self.GENERIC_TERMS)
        query_generic = any(term in normalized_query for term in self.GENERIC_TERMS)
        if not item_generic or query_generic:
            return False
        query_tokens = {token for token in re.split(r"\s+", normalized_query) if len(token) > 2}
        item_tokens = {token for token in re.split(r"\s+", item_text) if len(token) > 2}
        meaningful_overlap = query_tokens & item_tokens
        return len(meaningful_overlap) <= 2

    def _confidence_band(self, score: float) -> str:
        if score >= self.weights.strong_threshold:
            return "high"
        if score >= self.weights.threshold:
            return "medium"
        if score >= self.weights.review_threshold:
            return "low"
        return "very_low"

    @staticmethod
    def _flag_reasons(rationale: list[str], confidence_band: str) -> list[str]:
        reasons: list[str] = []
        for note in rationale:
            lowered = note.lower()
            if "unit mismatch" in lowered:
                reasons.append("unit_mismatch")
            elif "category mismatch" in lowered:
                reasons.append("category_mismatch")
            elif "section mismatch" in lowered:
                reasons.append("section_mismatch")
            elif "generic candidate match" in lowered:
                reasons.append("generic_match")
            elif "missing boq unit" in lowered:
                reasons.append("missing_unit")
            elif "unstable text score" in lowered:
                reasons.append("unstable_text_score")
        if confidence_band in {"low", "very_low"}:
            reasons.append(f"confidence_{confidence_band}")
        deduped: list[str] = []
        for reason in reasons:
            if reason not in deduped:
                deduped.append(reason)
        return deduped

    @staticmethod
    def _attribute_overlap(attribute_terms: set[str], item: RateItem) -> float:
        if not attribute_terms:
            return 0.0
        item_terms = {
            token
            for token in normalize_text(
                " ".join(
                    [
                        str(item.description or ""),
                        str(item.material_type or ""),
                        str(item.keywords or ""),
                        str(item.notes or ""),
                    ]
                )
            ).split()
            if len(token) > 2
        }
        if not item_terms:
            return 0.0
        overlap = len(attribute_terms & item_terms)
        return min(1.0, overlap / max(1, min(len(attribute_terms), 4)))

"""Matching engine for BOQ descriptions against the rate library."""

from __future__ import annotations

from dataclasses import dataclass
from math import fabs

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

    def match(self, line: BOQLine, region: str) -> MatchResult:
        """Return the best matching rate item for a BOQ line."""
        normalized_query, alias_hits = apply_aliases(line.description, self.aliases)
        line.normalized_description = normalized_query
        normalized_attributes = normalize_text(getattr(line, "spec_attributes", "") or "")
        attribute_terms = {token for token in normalized_attributes.split() if len(token) > 2}
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

            if line.inferred_section and item.section and line.inferred_section.lower() == item.section.lower():
                score += self.weights.section_bonus
                rationale.append("section-bonus")
            elif line.inferred_section and item.section:
                review_flags.append("section mismatch")

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
            ranked.append((score, item, rationale))

        ranked.sort(key=lambda entry: entry[0], reverse=True)
        if not ranked:
            return MatchResult(boq_line=line, decision="unmatched", review_flag=True, rationale=["no-active-items"])

        best_score, best_item, best_rationale = ranked[0]
        alternate_options = [
            f"{item.item_code} | {item.description} | {item.unit} | {item.rate:.2f} | {score:.1f}"
            for score, item, _ in ranked[1:4]
            if score >= self.weights.review_threshold
        ]

        decision = "matched" if best_score >= self.weights.threshold else "review"
        unit_mismatch_forced_review = any(note.startswith("unit mismatch:") for note in best_rationale)
        review_flag = (best_score < self.weights.strong_threshold) or unit_mismatch_forced_review
        commercial_review_flags = [note for note in best_rationale if "mismatch" in note or "missing" in note or "unstable" in note]
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
            commercial_review_flags=commercial_review_flags,
            rationale=best_rationale,
        )

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

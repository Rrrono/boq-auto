"""Pluggable matching engine with rule, AI, and hybrid modes."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
import math
from typing import Any

from rapidfuzz import fuzz

from src.cost_schema import CostDatabase
from src.learning_engine import LearningEngine
from src.models import AliasEntry
from src.normalizer import normalize_text, normalize_unit


@dataclass(slots=True)
class MatchCandidate:
    item: Any
    score: float
    mode: str
    rationale: list[str] = field(default_factory=list)


def _item_code(item: Any) -> str:
    return str(getattr(item, "item_code", getattr(item, "code", "")) or "")


def _item_description(item: Any) -> str:
    return str(getattr(item, "description", getattr(item, "item_name", "")) or "")


def _item_normalized_description(item: Any) -> str:
    return normalize_text(str(getattr(item, "normalized_description", "") or _item_description(item)))


def _item_unit(item: Any) -> str:
    return normalize_unit(str(getattr(item, "unit", "")))


def _item_category(item: Any) -> str:
    return str(getattr(item, "category", getattr(item, "section", "")) or "")


def _item_material(item: Any) -> str:
    return str(getattr(item, "material", "") or "")


def _item_keywords(item: Any) -> list[str]:
    keywords = getattr(item, "keywords", None)
    if isinstance(keywords, list):
        return [normalize_text(str(value)) for value in keywords if str(value).strip()]
    raw = str(getattr(item, "keywords", "") or "")
    return [normalize_text(value) for value in raw.split(",") if value.strip()]


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    numerator = sum(a * b for a, b in zip(left, right))
    left_mag = math.sqrt(sum(a * a for a in left))
    right_mag = math.sqrt(sum(b * b for b in right))
    if not left_mag or not right_mag:
        return 0.0
    return numerator / (left_mag * right_mag)


class MatchingEngine:
    def __init__(
        self,
        mode: str = "rule",
        config: Any | None = None,
        aliases: list[AliasEntry] | None = None,
        embedding_provider=None,
        embedding_lookup: dict[str, list[float]] | None = None,
        hybrid_ai_weight: float = 25.0,
        hybrid_weights: dict[str, float] | None = None,
        learning_engine: LearningEngine | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.config = config
        self.aliases = aliases or []
        self.embedding_provider = embedding_provider
        self.embedding_lookup = embedding_lookup or {}
        self.hybrid_ai_weight = hybrid_ai_weight
        self.learning_engine = learning_engine
        self.logger = logger or logging.getLogger("boq_auto")
        self.hybrid_weights = hybrid_weights or {
            "semantic": 0.45,
            "alias": 0.20,
            "unit": 0.15,
            "keyword": 0.20,
        }
        requested_mode = mode or str(config.get("matching.mode", "rule")) if config else mode
        self.requested_mode = (requested_mode or "rule").strip().lower()
        self.mode = self._resolve_mode(self.requested_mode)

    def _resolve_mode(self, requested_mode: str) -> str:
        if self.config is not None and not bool(self.config.get("ai.enabled", False)):
            self.logger.info("ai_disabled | AI disabled -> using rule mode")
            return "rule"
        if requested_mode in {"ai", "hybrid"} and self.embedding_provider is None:
            self.logger.warning("fallback_triggered | Embeddings unavailable -> fallback engaged")
            return "rule"
        return requested_mode or "rule"

    def match(self, query: str, items: list[Any]) -> list[MatchCandidate]:
        if self.mode == "ai":
            return self.ai_match(query, items)
        if self.mode == "hybrid":
            return self.hybrid_match(query, items)
        return self.rule_match(query, items)

    def rule_match(self, query: str, items: list[Any]) -> list[MatchCandidate]:
        normalized_query = self._apply_aliases(query)
        ranked: list[MatchCandidate] = []
        for item in items:
            description = _item_normalized_description(item)
            sort_score = fuzz.token_sort_ratio(normalized_query, description)
            set_score = fuzz.token_set_ratio(normalized_query, description)
            partial_score = fuzz.partial_ratio(normalized_query, description)
            score = (sort_score * 0.45) + (set_score * 0.35) + (partial_score * 0.20)
            rationale = [f"rule={score:.1f}", f"sort={sort_score:.1f}", f"set={set_score:.1f}"]
            learning_adjustment, learning_notes = self.learning_adjustment(normalized_query, _item_code(item))
            score += learning_adjustment
            rationale.extend(learning_notes)
            ranked.append(MatchCandidate(item=item, score=round(score, 2), mode="rule", rationale=rationale))
        return sorted(ranked, key=lambda candidate: candidate.score, reverse=True)

    def ai_match(self, query: str, items: list[Any]) -> list[MatchCandidate]:
        if self.embedding_provider is None:
            return []
        query_embedding = self.embedding_provider.embed(query)
        if not query_embedding:
            return []
        ranked: list[MatchCandidate] = []
        for item in items:
            embedding = self.embedding_lookup.get(_item_code(item))
            if not embedding:
                continue
            similarity = _cosine_similarity(query_embedding, embedding)
            ranked.append(
                MatchCandidate(
                    item=item,
                    score=round(similarity * 100, 2),
                    mode="ai",
                    rationale=[f"ai={similarity:.4f}", f"model={getattr(self.embedding_provider, 'model_name', 'unknown')}"],
                )
            )
        return sorted(ranked, key=lambda candidate: candidate.score, reverse=True)

    def hybrid_match(self, query: str, items: list[Any]) -> list[MatchCandidate]:
        rule_candidates = self.rule_match(query, items)
        if not rule_candidates:
            return []
        short_list = [candidate.item for candidate in rule_candidates[:25]]
        ai_candidates = self.ai_match(query, short_list)
        ai_scores = {_item_code(candidate.item): candidate for candidate in ai_candidates}
        normalized_query = self._apply_aliases(query)
        query_tokens = {token for token in normalized_query.split() if token}
        query_unit = self._detect_query_unit(query_tokens)
        alias_terms = self._alias_terms(normalized_query)
        ranked: list[MatchCandidate] = []
        for candidate in rule_candidates:
            item = candidate.item
            code = _item_code(item)
            ai_candidate = ai_scores.get(code)
            semantic_component = (ai_candidate.score / 100.0) if ai_candidate else (candidate.score / 100.0)
            alias_component = self._alias_match_score(alias_terms, item)
            unit_component = self._unit_similarity(query_unit, _item_unit(item))
            keyword_component = self._keyword_overlap(query_tokens, item)
            combined = (
                semantic_component * self.hybrid_weights.get("semantic", 0.45)
                + alias_component * self.hybrid_weights.get("alias", 0.20)
                + unit_component * self.hybrid_weights.get("unit", 0.15)
                + keyword_component * self.hybrid_weights.get("keyword", 0.20)
            )
            combined_score = round(combined * 100.0, 2)
            learning_adjustment, learning_notes = self.learning_adjustment(normalized_query, code)
            combined_score += learning_adjustment
            rationale = [
                f"semantic={semantic_component:.3f}",
                f"alias={alias_component:.3f}",
                f"unit={unit_component:.3f}",
                f"keyword={keyword_component:.3f}",
            ]
            rationale.extend(learning_notes)
            rationale.extend(candidate.rationale)
            ranked.append(MatchCandidate(item=candidate.item, score=round(combined_score, 2), mode="hybrid", rationale=rationale))
        return sorted(ranked, key=lambda candidate: candidate.score, reverse=True)

    def learning_adjustment(self, query: str, item_id: str) -> tuple[float, list[str]]:
        if self.learning_engine is None or not item_id:
            return 0.0, []
        return self.learning_engine.query_adjustment(query, item_id)

    def _apply_aliases(self, query: str) -> str:
        normalized = normalize_text(query)
        for entry in self.aliases:
            alias = normalize_text(entry.alias)
            canonical = normalize_text(entry.canonical_term)
            if alias and alias in normalized and canonical:
                normalized = normalized.replace(alias, canonical)
        return normalized

    def _alias_terms(self, normalized_query: str) -> set[str]:
        terms: set[str] = set()
        for entry in self.aliases:
            alias = normalize_text(entry.alias)
            canonical = normalize_text(entry.canonical_term)
            if alias and alias in normalized_query:
                terms.add(alias)
            if canonical and canonical in normalized_query:
                terms.add(canonical)
        return terms

    def _alias_match_score(self, alias_terms: set[str], item: Any) -> float:
        if not alias_terms:
            return 0.0
        description = _item_normalized_description(item)
        material = normalize_text(_item_material(item))
        category = normalize_text(_item_category(item))
        hits = sum(1 for term in alias_terms if term and (term in description or term == material or term == category))
        return min(1.0, hits / max(1, len(alias_terms)))

    def _unit_similarity(self, query_unit: str, item_unit: str) -> float:
        if not query_unit or not item_unit:
            return 0.0
        return 1.0 if query_unit == item_unit else 0.0

    def _keyword_overlap(self, query_tokens: set[str], item: Any) -> float:
        item_tokens = set(_item_keywords(item))
        item_tokens.update(token for token in _item_normalized_description(item).split() if token)
        if not query_tokens or not item_tokens:
            return 0.0
        overlap = len(query_tokens & item_tokens)
        return min(1.0, overlap / max(1, len(query_tokens)))

    def _detect_query_unit(self, query_tokens: set[str]) -> str:
        for token in query_tokens:
            normalized = normalize_unit(token)
            if normalized:
                return normalized
        return ""


def log_match_feedback(
    schema_path: str,
    query_text: str,
    selected_item_id: str,
    action: str,
    alternative_item_id: str | None = None,
) -> None:
    """Persist UI feedback for future tuning without affecting current matching behavior."""

    repository = CostDatabase(schema_path)
    selected_resolved = repository.resolve_item_id(selected_item_id) or selected_item_id
    alternative_resolved = repository.resolve_item_id(alternative_item_id or "") or str(alternative_item_id or "")
    repository.log_match_feedback(
        query_text=query_text,
        item_id=selected_resolved,
        action=str(action or "").strip().lower() or "accepted",
        alternative_item_id=alternative_resolved,
    )

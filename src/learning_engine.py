"""Rule-based learning loop driven by stored user feedback."""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
import json
import re
from typing import Any

from rapidfuzz import fuzz

from src.cost_schema import CostDatabase, MatchFeedback


_PUNCT_RE = re.compile(r"[^a-z0-9\s]+")


def _stem_token(token: str) -> str:
    if token.endswith("ies") and len(token) > 4:
        return token[:-3] + "y"
    for suffix in ("ing", "ed", "es", "s"):
        if token.endswith(suffix) and len(token) > len(suffix) + 2:
            return token[: -len(suffix)]
    return token


def normalize_query(query: str) -> str:
    normalized = _PUNCT_RE.sub(" ", str(query or "").lower())
    tokens = [_stem_token(token) for token in normalized.split() if token.strip()]
    tokens.sort()
    return " ".join(tokens)


class LearningEngine:
    """In-memory lookup engine for accepted, corrected, and rejected matches."""

    def __init__(self, feedback: list[MatchFeedback] | None = None) -> None:
        self.feedback = list(feedback or [])
        self.preferred_map: dict[str, str] = {}
        self.rejected_map: dict[str, set[str]] = defaultdict(set)
        self.accepted_counts: Counter[str] = Counter()
        self.rejected_counts: Counter[str] = Counter()
        self.corrected_queries: Counter[str] = Counter()
        self._build_indexes()

    @classmethod
    def from_schema(cls, schema_path: str | Path) -> "LearningEngine":
        repository = CostDatabase(schema_path)
        return cls(repository.fetch_match_feedback())

    def _build_indexes(self) -> None:
        accepted_by_query: dict[str, Counter[str]] = defaultdict(Counter)
        corrected_by_query: dict[str, str] = {}
        for entry in self.feedback:
            normalized = normalize_query(entry.query_text)
            if not normalized:
                continue
            if entry.action == "accepted":
                accepted_by_query[normalized][entry.item_id] += 1
                self.accepted_counts[entry.item_id] += 1
            elif entry.action == "rejected":
                self.rejected_map[normalized].add(entry.item_id)
                self.rejected_counts[entry.item_id] += 1
            elif entry.action == "corrected":
                preferred = entry.alternative_item_id or entry.item_id
                if preferred:
                    corrected_by_query[normalized] = preferred
                    self.accepted_counts[preferred] += 1
                    self.corrected_queries[normalized] += 1
                if entry.item_id:
                    self.rejected_map[normalized].add(entry.item_id)
                    self.rejected_counts[entry.item_id] += 1
        for normalized, counter in accepted_by_query.items():
            if normalized in corrected_by_query:
                self.preferred_map[normalized] = corrected_by_query[normalized]
            elif counter:
                self.preferred_map[normalized] = counter.most_common(1)[0][0]
        for normalized, preferred in corrected_by_query.items():
            self.preferred_map[normalized] = preferred

    def has_feedback(self) -> bool:
        return bool(self.feedback)

    def preferred_item(self, query_text: str) -> str:
        normalized = normalize_query(query_text)
        if normalized in self.preferred_map:
            return self.preferred_map[normalized]
        return self._fuzzy_lookup(normalized, self.preferred_map)

    def rejected_items(self, query_text: str) -> set[str]:
        normalized = normalize_query(query_text)
        direct = self.rejected_map.get(normalized)
        if direct:
            return set(direct)
        best_key = self._best_match_key(normalized, self.rejected_map.keys())
        return set(self.rejected_map.get(best_key, set()))

    def acceptance_weight(self, item_id: str) -> float:
        accepted = self.accepted_counts.get(item_id, 0)
        rejected = self.rejected_counts.get(item_id, 0)
        return min(4.0, accepted * 0.75) - min(3.0, rejected * 0.5)

    def query_adjustment(self, query_text: str, item_id: str) -> tuple[float, list[str]]:
        notes: list[str] = []
        score = 0.0
        preferred = self.preferred_item(query_text)
        rejected = self.rejected_items(query_text)
        if preferred and item_id == preferred:
            score += 25.0
            notes.append("learning-preferred")
        if item_id in rejected:
            score -= 20.0
            notes.append("learning-rejected")
        population_adjustment = self.acceptance_weight(item_id)
        if population_adjustment:
            score += population_adjustment
            notes.append(f"learning-history={population_adjustment:.2f}")
        return score, notes

    def export_learning_data(self) -> dict[str, Any]:
        return {
            "feedback_count": len(self.feedback),
            "preferred_queries": self.preferred_map,
            "rejected_queries": {key: sorted(values) for key, values in self.rejected_map.items()},
            "accepted_counts": dict(self.accepted_counts),
            "rejected_counts": dict(self.rejected_counts),
            "corrected_queries": dict(self.corrected_queries),
        }

    def export_learning_data_file(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.export_learning_data(), indent=2, ensure_ascii=True), encoding="utf-8")
        return target

    def feedback_insights(self, limit: int = 10) -> dict[str, list[dict[str, Any]]]:
        return {
            "top_corrected_queries": [
                {"query": query, "count": count, "preferred_item_id": self.preferred_map.get(query, "")}
                for query, count in self.corrected_queries.most_common(limit)
            ],
            "most_rejected_items": [
                {"item_id": item_id, "count": count}
                for item_id, count in self.rejected_counts.most_common(limit)
            ],
            "most_accepted_items": [
                {"item_id": item_id, "count": count}
                for item_id, count in self.accepted_counts.most_common(limit)
            ],
        }

    def _fuzzy_lookup(self, normalized: str, lookup: dict[str, str]) -> str:
        best_key = self._best_match_key(normalized, lookup.keys())
        return lookup.get(best_key, "")

    @staticmethod
    def _best_match_key(normalized: str, keys) -> str:
        best_key = ""
        best_score = 0.0
        for key in keys:
            score = fuzz.token_sort_ratio(normalized, key)
            if score > best_score and score >= 85:
                best_score = score
                best_key = key
        return best_key


def export_learning_data(schema_path: str | Path, output_path: str | Path) -> Path:
    """Export persisted learning feedback into JSON for backup or analysis."""

    learning = LearningEngine.from_schema(schema_path)
    return learning.export_learning_data_file(output_path)

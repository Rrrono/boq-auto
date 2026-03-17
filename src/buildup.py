"""Build-up fallback pricing support."""

from __future__ import annotations

from collections import defaultdict

from rapidfuzz import fuzz

from .models import BuildUpInput, BuildUpRecipeLine, MatchResult, BOQLine
from .normalizer import normalize_text, normalize_unit


def price_build_up_recipe(
    line: BOQLine,
    recipes: list[BuildUpRecipeLine],
    inputs: list[BuildUpInput],
    region: str,
    threshold: float = 78,
) -> MatchResult | None:
    """Attempt to price a BOQ line from build-up recipes."""
    if not line.description:
        return None

    grouped: dict[str, list[BuildUpRecipeLine]] = defaultdict(list)
    for recipe in recipes:
        grouped[recipe.recipe_id].append(recipe)

    input_map: dict[str, list[BuildUpInput]] = defaultdict(list)
    for entry in inputs:
        if entry.active:
            input_map[entry.input_code].append(entry)

    best: MatchResult | None = None
    query = normalize_text(line.description)
    for recipe_id, recipe_lines in grouped.items():
        head = recipe_lines[0]
        score = fuzz.token_sort_ratio(query, normalize_text(head.output_description))
        if head.section and line.inferred_section and head.section.lower() == line.inferred_section.lower():
            score += 8
        if line.unit and head.output_unit and normalize_unit(line.unit) == normalize_unit(head.output_unit):
            score += 6
        if score < 60:
            continue

        total = 0.0
        missing_components: list[str] = []
        for component in recipe_lines:
            candidates = [
                item for item in input_map.get(component.component_code, [])
                if item.region.lower() == region.lower()
            ] or input_map.get(component.component_code, [])
            if not candidates:
                missing_components.append(component.component_code)
                continue
            rate = candidates[0].rate
            total += rate * component.factor * (1 + component.waste_factor)

        if missing_components:
            continue

        candidate = MatchResult(
            boq_line=line,
            decision="matched" if score >= threshold else "review",
            matched_item_code=recipe_id,
            matched_description=head.output_description,
            matched_unit=head.output_unit,
            base_rate=round(total, 2),
            rate=round(total, 2),
            confidence_score=min(score, 95),
            review_flag=score < threshold,
            section_used=head.section,
            source="BuildUpRecipes",
            region_used=region,
            built_up=True,
            basis_of_rate=f"Build-up recipe {recipe_id}",
            rationale=["build-up fallback", f"recipe {recipe_id}"],
        )
        if not best or candidate.confidence_score > best.confidence_score:
            best = candidate
    return best

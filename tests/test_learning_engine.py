from src.learning_engine import LearningEngine, normalize_query
from src.matching_engine import MatchingEngine, log_match_feedback
from src.models import RateItem


def _item(code: str, description: str) -> RateItem:
    return RateItem(
        item_code=code,
        description=description,
        normalized_description=description.lower(),
        section="earthworks",
        subsection="",
        unit="m3",
        rate=100.0,
        currency="KES",
        region="",
        source="test",
        source_sheet="",
        source_page="",
        basis="",
        crew_type="",
        plant_type="",
        material_type="",
        keywords="excavation, trench",
        alias_group="",
        build_up_recipe_id="",
        confidence_hint=0.0,
        notes="",
        active=True,
    )


def test_feedback_stored_correctly(tmp_path) -> None:
    schema_path = tmp_path / "rates.sqlite"
    from src.cost_schema import CostDatabase, build_cost_item

    repository = CostDatabase(schema_path)
    source = repository.register_source("Manual", "v1", "manual.pdf")
    item = build_cost_item("A1", "Excavation", "m3", "earthworks", "", "soil", ["excavation"], 1000.0, source.id)
    repository.insert_items([item])

    log_match_feedback(str(schema_path), "Excavation for trenches", "A1", "accepted")

    feedback = repository.fetch_match_feedback()
    assert len(feedback) == 1
    assert feedback[0].query_text == "Excavation for trenches"
    assert feedback[0].item_id == item.id
    assert feedback[0].action == "accepted"


def test_preference_overrides_matching() -> None:
    items = [_item("A1", "excavation in trench"), _item("A2", "selected fill")]
    from src.cost_schema import MatchFeedback

    learning = LearningEngine(
        [
            MatchFeedback(
                id="1",
                query_text="trench excavation",
                item_id="A1",
                action="accepted",
                alternative_item_id="",
                timestamp="2026-03-19T10:00:00+00:00",
            )
        ]
    )
    engine = MatchingEngine(mode="rule", learning_engine=learning)

    results = engine.match("excavate trench", items)

    assert results[0].item.item_code == "A1"
    assert any("learning-preferred" in note for note in results[0].rationale)


def test_rejection_reduces_score() -> None:
    items = [_item("A1", "excavation in trench"), _item("A2", "selected fill")]
    from src.cost_schema import MatchFeedback

    learning = LearningEngine(
        [
            MatchFeedback(
                id="1",
                query_text="excavate trench",
                item_id="A1",
                action="rejected",
                alternative_item_id="",
                timestamp="2026-03-19T10:00:00+00:00",
            )
        ]
    )
    engine = MatchingEngine(mode="rule", learning_engine=learning)

    results = engine.match("trench excavation", items)

    rejected_result = next(candidate for candidate in results if candidate.item.item_code == "A1")
    assert any("learning-rejected" in note for note in rejected_result.rationale)


def test_corrected_match_overrides_everything() -> None:
    items = [_item("A1", "excavation in trench"), _item("A2", "selected fill material")]
    from src.cost_schema import MatchFeedback

    learning = LearningEngine(
        [
            MatchFeedback(
                id="1",
                query_text="backfill trenches",
                item_id="A1",
                action="corrected",
                alternative_item_id="A2",
                timestamp="2026-03-19T10:00:00+00:00",
            )
        ]
    )
    engine = MatchingEngine(mode="rule", learning_engine=learning)

    results = engine.match("trench backfilling", items)

    assert normalize_query("backfill trenches") == normalize_query("trench backfilling")
    assert results[0].item.item_code == "A2"
    assert any("learning-preferred" in note for note in results[0].rationale)

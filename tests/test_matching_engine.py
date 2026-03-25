from src.ai.embedding_provider import EmbeddingProvider, HashEmbeddingProvider, OpenAIEmbeddingProvider
from src.matching_engine import MatchingEngine
from src.models import AliasEntry, RateItem


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
        keywords="",
        alias_group="",
        build_up_recipe_id="",
        confidence_hint=0.0,
        notes="",
        active=True,
    )


class FixedEmbeddingProvider(EmbeddingProvider):
    model_name = "fixed"

    def __init__(self, vectors: dict[str, list[float]]) -> None:
        self.vectors = vectors

    def available(self) -> bool:
        return True

    def embed(self, text: str) -> list[float]:
        return self.vectors.get(text, [])


def test_rule_matching_prefers_keyword_and_alias_hits() -> None:
    items = [_item("A1", "excavation and disposal"), _item("A2", "selected fill")]
    aliases = [AliasEntry(alias="backfilling", canonical_term="selected fill", section_bias="earthworks")]
    engine = MatchingEngine(mode="rule", aliases=aliases)

    results = engine.match("Backfilling to trenches", items)

    assert results[0].item.item_code == "A2"


def test_hybrid_matching_uses_ai_to_rank_shortlist() -> None:
    items = [_item("A1", "excavation and disposal"), _item("A2", "selected fill")]
    provider = FixedEmbeddingProvider(
        {
            "fill work": [1.0, 0.0],
            "excavation and disposal": [0.0, 1.0],
            "selected fill": [1.0, 0.0],
        }
    )
    engine = MatchingEngine(
        mode="hybrid",
        embedding_provider=provider,
        embedding_lookup={"A1": [0.0, 1.0], "A2": [1.0, 0.0]},
    )

    results = engine.match("fill work", items)

    assert results[0].item.item_code == "A2"
    assert any("semantic=" in note for note in results[0].rationale)


def test_ai_fallback_returns_no_embeddings_without_api_key() -> None:
    provider = OpenAIEmbeddingProvider(api_key="")
    engine = MatchingEngine(mode="ai", embedding_provider=provider, embedding_lookup={"A1": [1.0, 0.0]})

    results = engine.match("excavation", [_item("A1", "excavation")])

    assert results == []


def test_hash_embedding_provider_returns_vector() -> None:
    provider = HashEmbeddingProvider()
    embedding = provider.embed("excavation in trench")

    assert embedding


def test_hybrid_matching_uses_unit_and_keyword_signals() -> None:
    first = _item("A1", "excavation in trench")
    second = _item("A2", "painting works")
    second.unit = "m2"
    second.keywords = "paint, finish"
    provider = FixedEmbeddingProvider(
        {
            "earthworks | soil | excavation trench | m3": [1.0, 0.0],
        }
    )
    engine = MatchingEngine(
        mode="hybrid",
        embedding_provider=provider,
        embedding_lookup={"A1": [1.0, 0.0], "A2": [0.0, 1.0]},
    )

    results = engine.match("excavation trench m3", [first, second])

    assert results[0].item.item_code == "A1"


def test_openai_provider_normalizes_structured_ingestion_suggestions(monkeypatch) -> None:
    provider = OpenAIEmbeddingProvider(api_key="test-key", task_model="gpt-4.1-mini")
    monkeypatch.setattr(
        provider,
        "_complete_json",
        lambda system_prompt, user_prompt: {
            "aliases": ["soil excavation", "Soil Excavation", "Excavate trench soil"],
            "category": "earthworks",
            "material": "soil",
            "keywords": ["excavation", "trench", "soil", "excavation"],
        },
    )

    payload = provider.suggest_ingestion_attributes("Excavation in trench soil", unit="m3", section="Earthworks")

    assert payload["category"] == "earthworks"
    assert payload["material"] == "soil"
    assert payload["aliases"] == ["soil excavation", "Excavate trench soil"]
    assert payload["keywords"] == ["excavation", "trench", "soil"]
    assert provider.suggest_aliases("Excavation in trench soil") == ["soil excavation", "Excavate trench soil"]


def test_openai_provider_normalizes_boq_item_extraction(monkeypatch) -> None:
    provider = OpenAIEmbeddingProvider(api_key="test-key", task_model="gpt-4.1-mini")
    monkeypatch.setattr(
        provider,
        "_complete_json",
        lambda system_prompt, user_prompt: {
            "items": [
                {"description": "LED light fittings complete", "unit": "nr", "reason": "Explicit fitting item.", "attributes": ["600 x 600", "LED"]},
                {"description": "LED light fittings complete", "unit": "nr", "reason": "Duplicate wording."},
                {"description": "Testing and commissioning", "unit": "sum", "reason": "Commissioning clause.", "attributes": ["Electrical system"]},
            ]
        },
    )

    items = provider.extract_boq_items("Supply and install LED light fittings complete with testing.")

    assert items == [
        {"description": "LED light fittings complete", "unit": "nr", "reason": "Explicit fitting item.", "attributes": ["600 x 600", "LED"]},
        {"description": "Testing and commissioning", "unit": "sum", "reason": "Commissioning clause.", "attributes": ["Electrical system"]},
    ]

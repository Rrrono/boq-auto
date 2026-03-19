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

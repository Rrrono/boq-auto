from src.ai.embedding_provider import get_embedding_provider
from src.matching_engine import MatchingEngine
from src.models import AppConfig, RateItem


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
        keywords="excavation, disposal",
        alias_group="",
        build_up_recipe_id="",
        confidence_hint=0.0,
        notes="",
        active=True,
    )


def test_ai_disabled_forces_rule_mode() -> None:
    config = AppConfig(data={"ai": {"enabled": False}, "matching": {"mode": "ai"}})
    engine = MatchingEngine(mode="ai", config=config, embedding_provider=None)

    results = engine.match("excavation", [_item("A1", "excavation in trench")])

    assert engine.mode == "rule"
    assert results
    assert results[0].mode == "rule"


def test_missing_api_key_returns_no_provider_and_rule_fallback(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    config = AppConfig(
        data={
            "ai": {"enabled": True, "provider": "openai", "model": "text-embedding-3-small", "use_env_key": True},
            "matching": {"mode": "ai"},
        }
    )

    provider = get_embedding_provider(config)
    engine = MatchingEngine(mode="ai", config=config, embedding_provider=provider)
    results = engine.match("selected fill", [_item("A1", "selected fill material")])

    assert provider is None
    assert engine.mode == "rule"
    assert results
    assert results[0].item.item_code == "A1"


def test_hybrid_without_embeddings_executes_safely() -> None:
    config = AppConfig(data={"ai": {"enabled": True}, "matching": {"mode": "hybrid"}})
    items = [_item("A1", "excavation and disposal"), _item("A2", "selected fill")]
    engine = MatchingEngine(mode="hybrid", config=config, embedding_provider=None)

    results = engine.match("selected fill m3", items)

    assert engine.mode == "rule"
    assert results
    assert results[0].item.item_code == "A2"
    assert all(candidate.mode == "rule" for candidate in results)

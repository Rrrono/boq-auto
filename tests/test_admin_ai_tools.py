from src.ai.admin_tools import generate_embeddings, get_embedding_stats, reset_embeddings, test_ai_connection
from src.cost_schema import CostDatabase, build_cost_item
from src.models import AppConfig


class FixedProvider:
    model_name = "fixed-test"

    def embed(self, text: str) -> list[float]:
        if not text.strip():
            return []
        return [0.5, 0.5, 0.5]


def _seed_repository(tmp_path):
    repository = CostDatabase(tmp_path / "master.xlsx")
    source = repository.register_source("Manual", "v1", "manual.pdf")
    item = build_cost_item("A1", "Excavation", "m3", "earthworks", "", "soil", ["excavation"], 1000.0, source.id)
    repository.insert_items([item])
    return repository, item


def test_ai_disabled_safe_skip() -> None:
    config = AppConfig(data={"ai": {"enabled": False}})

    success, message, provider = test_ai_connection(config)

    assert success is False
    assert provider is None
    assert "disabled" in message.lower()


def test_no_api_key_graceful_fail(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    config = AppConfig(data={"ai": {"enabled": True, "provider": "openai", "model": "text-embedding-3-small", "use_env_key": True}})

    success, message, provider = test_ai_connection(config)

    assert success is False
    assert provider is None
    assert "fallback" in message.lower() or "unavailable" in message.lower()


def test_embedding_generation_works_when_provider_exists(tmp_path) -> None:
    repository, _item = _seed_repository(tmp_path)

    generated = generate_embeddings(repository, FixedProvider())
    stats = get_embedding_stats(repository)

    assert generated == 1
    assert stats["total_items"] == 1
    assert stats["embedded_items"] == 1
    assert stats["last_updated"]


def test_reset_embeddings_clears_records(tmp_path) -> None:
    repository, item = _seed_repository(tmp_path)
    repository.save_embedding(item.id, [0.1, 0.2], "fixed-test")

    removed = reset_embeddings(repository)
    stats = get_embedding_stats(repository)

    assert removed == 1
    assert stats["embedded_items"] == 0

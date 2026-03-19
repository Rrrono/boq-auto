"""Admin-only helpers for safe AI testing and embedding management."""

from __future__ import annotations

from typing import Any

from src.ai.embedding_provider import get_embedding_provider
from src.cost_schema import CostDatabase, composed_embedding_text


def test_ai_connection(config: Any) -> tuple[bool, str, Any]:
    """Try to initialize and lightly exercise the current embedding provider."""

    provider = get_embedding_provider(config)
    if provider is None:
        if not bool(config.get("ai.enabled", False)):
            return False, "AI is disabled. Rule mode remains active.", None
        return False, "AI unavailable. Fallback will be used.", None

    try:
        embedding = provider.embed("boq auto ai connection test")
    except Exception:
        return False, "AI unavailable. Fallback will be used.", None
    if not embedding:
        return False, "AI unavailable. Fallback will be used.", None
    return True, f"AI connection successful using {getattr(provider, 'model_name', 'unknown')}.", provider


def generate_embeddings(schema_db: CostDatabase, provider: Any) -> int:
    """Generate or refresh embeddings for all stored items."""

    if provider is None:
        return 0
    generated = 0
    for item in schema_db.fetch_items():
        embedding = provider.embed(composed_embedding_text(item))
        if not embedding:
            continue
        schema_db.save_embedding(item.id, embedding, getattr(provider, "model_name", "unknown"))
        generated += 1
    return generated


def reset_embeddings(schema_db: CostDatabase) -> int:
    """Clear all stored item embeddings."""

    return schema_db.clear_embeddings()


def get_embedding_stats(schema_db: CostDatabase) -> dict[str, Any]:
    """Return lightweight embedding status for the admin UI."""

    return schema_db.fetch_embedding_stats()

"""Pluggable embedding providers with safe fallback behavior."""

from __future__ import annotations

import hashlib
import logging
import math
import os


LOGGER = logging.getLogger("boq_auto")


class EmbeddingProvider:
    """Base embedding provider interface."""

    model_name = "disabled"

    def available(self) -> bool:
        return False

    def embed(self, text: str) -> list[float]:
        return []

    def suggest_aliases(self, text: str) -> list[str]:
        return []


class HashEmbeddingProvider(EmbeddingProvider):
    """Deterministic local embedding provider for testing and offline ranking."""

    model_name = "hash-local-v1"

    def available(self) -> bool:
        return True

    def embed(self, text: str) -> list[float]:
        tokens = [token for token in text.lower().split() if token]
        if not tokens:
            return []
        vector = [0.0] * 16
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            for index in range(len(vector)):
                vector[index] += digest[index] / 255.0
        magnitude = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [round(value / magnitude, 6) for value in vector]


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI-ready provider that degrades safely when unavailable."""

    def __init__(self, model: str = "text-embedding-3-small", api_key: str | None = None) -> None:
        self.model_name = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")

    def available(self) -> bool:
        return bool(self.api_key)

    def embed(self, text: str) -> list[float]:
        if not self.available():
            return []
        try:
            from openai import OpenAI  # type: ignore
        except Exception:
            return []
        try:
            client = OpenAI(api_key=self.api_key)
            response = client.embeddings.create(model=self.model_name, input=text)
            if not response.data:
                return []
            return list(response.data[0].embedding)
        except Exception:
            LOGGER.warning("ai_init_failed | embedding request failed", exc_info=True)
            return []

    def suggest_aliases(self, text: str) -> list[str]:
        return []


def get_embedding_provider(config) -> EmbeddingProvider | None:
    """Initialize an embedding provider safely, or return None."""

    if not bool(config.get("ai.enabled", False)):
        LOGGER.info("ai_disabled | AI disabled in config")
        return None

    provider_name = str(config.get("ai.provider", "openai")).strip().lower()
    model_name = str(config.get("ai.model", config.get("ai.embedding_model", "text-embedding-3-small"))).strip()

    try:
        if provider_name == "openai":
            api_key = os.getenv("OPENAI_API_KEY", "") if bool(config.get("ai.use_env_key", True)) else ""
            provider = OpenAIEmbeddingProvider(model=model_name, api_key=api_key)
            if not provider.available():
                LOGGER.warning("ai_init_failed | OPENAI_API_KEY missing or provider unavailable")
                return None
            return provider
    except Exception:
        LOGGER.warning("ai_init_failed | provider initialization failed", exc_info=True)
        return None

    LOGGER.warning("ai_init_failed | unknown provider '%s'", provider_name)
    return None

"""Pluggable embedding providers with safe fallback behavior."""

from __future__ import annotations

import hashlib
import math
import os


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
        client = OpenAI(api_key=self.api_key)
        response = client.embeddings.create(model=self.model_name, input=text)
        if not response.data:
            return []
        return list(response.data[0].embedding)

    def suggest_aliases(self, text: str) -> list[str]:
        return []

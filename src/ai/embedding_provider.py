"""Pluggable embedding providers with safe fallback behavior."""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
from typing import Any


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

    def suggest_ingestion_attributes(
        self,
        description: str,
        *,
        unit: str = "",
        section: str = "",
        region: str = "",
    ) -> dict[str, Any]:
        return {}

    def extract_boq_items(
        self,
        text: str,
        *,
        section: str = "",
        region: str = "",
    ) -> list[dict[str, Any]]:
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

    def __init__(
        self,
        model: str = "text-embedding-3-small",
        api_key: str | None = None,
        task_model: str = "gpt-4.1-mini",
    ) -> None:
        self.model_name = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.task_model = task_model

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
        payload = self.suggest_ingestion_attributes(text)
        aliases = payload.get("aliases", []) if isinstance(payload, dict) else []
        return [str(alias).strip() for alias in aliases if str(alias).strip()]

    def suggest_ingestion_attributes(
        self,
        description: str,
        *,
        unit: str = "",
        section: str = "",
        region: str = "",
    ) -> dict[str, Any]:
        if not self.available() or not str(description or "").strip():
            return {}
        system_prompt = (
            "You assist a construction estimating database ingestion workflow. "
            "Return strict JSON only. Be conservative and never invent rates, quantities, or codes. "
            "Your job is limited to lightweight enrichment for a single BOQ or manual item. "
            "Only suggest aliases that are close paraphrases or common estimator terms for the same item. "
            "If uncertain, return empty strings or empty arrays."
        )
        user_prompt = (
            "Extract cautious ingestion suggestions for this construction cost item.\n"
            f"Description: {str(description or '').strip()}\n"
            f"Unit: {str(unit or '').strip()}\n"
            f"Section: {str(section or '').strip()}\n"
            f"Region: {str(region or '').strip()}\n\n"
            "Return JSON with this exact shape:\n"
            "{\n"
            '  "aliases": ["..."],\n'
            '  "category": "",\n'
            '  "material": "",\n'
            '  "keywords": ["..."]\n'
            "}\n"
            "Rules:\n"
            "- aliases: maximum 5 short alternatives, no duplicates, no generic phrases.\n"
            "- category: one short trade/category label only if clear.\n"
            "- material: one short material label only if clear.\n"
            "- keywords: maximum 6 practical search keywords.\n"
            "- never include numbers unless essential to meaning.\n"
            "- never explain your answer.\n"
            "- return JSON only."
        )
        payload = self._complete_json(system_prompt, user_prompt)
        return self._normalize_ingestion_payload(payload, description)

    def extract_boq_items(
        self,
        text: str,
        *,
        section: str = "",
        region: str = "",
    ) -> list[dict[str, Any]]:
        if not self.available() or not str(text or "").strip():
            return []
        system_prompt = (
            "You assist a review-first construction estimating workflow. "
            "Return strict JSON only. "
            "Extract possible BOQ line-item candidates from one tender/specification clause. "
            "Do not invent quantities, rates, brands, or dimensions that are not present. "
            "Prefer concise estimator wording. If uncertain, return an empty list."
        )
        user_prompt = (
            "Extract cautious draft BOQ candidate items from this tender/spec clause.\n"
            f"Section: {str(section or '').strip()}\n"
            f"Region: {str(region or '').strip()}\n"
            f"Clause: {str(text or '').strip()}\n\n"
            "Return JSON with this exact shape:\n"
            "{\n"
            '  "items": [\n'
            '    {"description": "", "unit": "", "reason": "", "attributes": ["..."]}\n'
            "  ]\n"
            "}\n"
            "Rules:\n"
            "- maximum 4 items.\n"
            "- description must be short BOQ-style wording.\n"
            "- unit must be one of: m, m2, m3, nr, kg, sum, item, or empty.\n"
            "- reason must be brief and factual.\n"
            "- attributes: maximum 5 short technical attributes such as size, type, finish, rating, location, or installation requirement.\n"
            "- no prose outside JSON."
        )
        payload = self._complete_json(system_prompt, user_prompt)
        if not isinstance(payload, dict):
            return []
        items = payload.get("items", [])
        if not isinstance(items, list):
            return []
        normalized_items: list[dict[str, Any]] = []
        seen: set[str] = set()
        for raw in items:
            if not isinstance(raw, dict):
                continue
            description = " ".join(str(raw.get("description", "") or "").split()).strip(" -.,;:")
            unit = " ".join(str(raw.get("unit", "") or "").split()).strip().lower()
            reason = " ".join(str(raw.get("reason", "") or "").split()).strip()
            attributes: list[str] = []
            for value in raw.get("attributes", []) if isinstance(raw.get("attributes", []), list) else []:
                attribute = " ".join(str(value or "").split()).strip(" -.,;:")
                if not attribute:
                    continue
                if attribute.lower() in {existing.lower() for existing in attributes}:
                    continue
                attributes.append(attribute)
                if len(attributes) >= 5:
                    break
            if not description or len(description.split()) < 3:
                continue
            signature = description.lower()
            if signature in seen:
                continue
            seen.add(signature)
            normalized_items.append(
                {
                    "description": description,
                    "unit": unit if unit in {"m", "m2", "m3", "nr", "kg", "sum", "item"} else "",
                    "reason": reason,
                    "attributes": attributes,
                }
            )
            if len(normalized_items) >= 4:
                break
        return normalized_items

    def _client(self):
        try:
            from openai import OpenAI  # type: ignore
        except Exception:
            return None
        return OpenAI(api_key=self.api_key)

    def _complete_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        client = self._client()
        if client is None:
            return {}
        try:
            response = client.chat.completions.create(
                model=self.task_model,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            content = ""
            if getattr(response, "choices", None):
                message = response.choices[0].message
                content = str(getattr(message, "content", "") or "")
            return json.loads(content) if content else {}
        except Exception:
            LOGGER.warning("ai_init_failed | task request failed", exc_info=True)
            return {}

    def _normalize_ingestion_payload(self, payload: dict[str, Any], description: str) -> dict[str, Any]:
        if not isinstance(payload, dict):
            return {}
        canonical = " ".join(str(description or "").split()).strip().lower()
        aliases: list[str] = []
        for value in payload.get("aliases", []) if isinstance(payload.get("aliases", []), list) else []:
            alias = " ".join(str(value or "").split()).strip(" -.,;:")
            if not alias or alias.lower() == canonical:
                continue
            if alias.lower() in {existing.lower() for existing in aliases}:
                continue
            aliases.append(alias)
            if len(aliases) >= 5:
                break
        keywords: list[str] = []
        for value in payload.get("keywords", []) if isinstance(payload.get("keywords", []), list) else []:
            keyword = " ".join(str(value or "").split()).strip(" -.,;:")
            if not keyword:
                continue
            if keyword.lower() in {existing.lower() for existing in keywords}:
                continue
            keywords.append(keyword)
            if len(keywords) >= 6:
                break
        return {
            "aliases": aliases,
            "category": " ".join(str(payload.get("category", "") or "").split()).strip(),
            "material": " ".join(str(payload.get("material", "") or "").split()).strip(),
            "keywords": keywords,
        }


def get_embedding_provider(config) -> EmbeddingProvider | None:
    """Initialize an embedding provider safely, or return None."""

    if not bool(config.get("ai.enabled", False)):
        LOGGER.info("ai_disabled | AI disabled in config")
        return None

    provider_name = str(config.get("ai.provider", "openai")).strip().lower()
    model_name = str(config.get("ai.model", config.get("ai.embedding_model", "text-embedding-3-small"))).strip()
    task_model = str(config.get("ai.task_model", "gpt-4.1-mini")).strip() or "gpt-4.1-mini"

    try:
        if provider_name == "openai":
            api_key = os.getenv("OPENAI_API_KEY", "") if bool(config.get("ai.use_env_key", True)) else ""
            provider = OpenAIEmbeddingProvider(model=model_name, api_key=api_key, task_model=task_model)
            if not provider.available():
                LOGGER.warning("ai_init_failed | OPENAI_API_KEY missing or provider unavailable")
                return None
            return provider
    except Exception:
        LOGGER.warning("ai_init_failed | provider initialization failed", exc_info=True)
        return None

    LOGGER.warning("ai_init_failed | unknown provider '%s'", provider_name)
    return None

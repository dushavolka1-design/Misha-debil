from __future__ import annotations

import os
from typing import Any
from uuid import UUID

from dar.providers.ports import LLMProvider, LlmAnalysisResult


class RuPrivateLLMProvider(LLMProvider):
    """Russian private LLM contour — credentials, no-training and retention flags required."""

    name = "ru_private_llm"
    model_version = "ru-private-llm-v1"

    def __init__(self) -> None:
        self._endpoint = os.environ.get("RU_LLM_ENDPOINT", "").strip()
        self._api_key = os.environ.get("RU_LLM_API_KEY", "").strip()
        self._no_training = os.environ.get("RU_LLM_NO_TRAINING", "").lower() in {"1", "true", "yes"}
        self._retention_zero = os.environ.get("RU_LLM_RETENTION_ZERO", "").lower() in {"1", "true", "yes"}
        if not self._endpoint or not self._api_key:
            raise RuntimeError(
                "RU_LLM_ENDPOINT and RU_LLM_API_KEY required for ru_private_llm; "
                "do not send personal data until configured",
            )
        if not self._no_training or not self._retention_zero:
            raise RuntimeError(
                "RU_LLM_NO_TRAINING=true and RU_LLM_RETENTION_ZERO=true required before sending fragments",
            )

    async def extract_facts(
        self,
        *,
        fragment: str,
        document_id: UUID,
        json_schema: dict[str, Any],
        system_instructions: str,
        prompt_version: str,
    ) -> LlmAnalysisResult:
        _ = (fragment, document_id, json_schema, system_instructions, prompt_version)
        raise RuntimeError("ru_private_llm HTTP adapter not wired in this build")

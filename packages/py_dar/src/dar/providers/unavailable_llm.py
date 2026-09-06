from __future__ import annotations

from typing import Any
from uuid import UUID

from dar.providers.ports import LlmAnalysisResult, LLMProvider


class UnavailableLLMProvider(LLMProvider):
    """Placeholder when external LLM is not configured — pipeline uses local rules."""

    name = "unavailable"
    model_version = "none"

    async def analyze_document(
        self,
        *,
        text: str,
        document_id: UUID,
        purpose: str,
    ) -> LlmAnalysisResult:
        _ = (text, document_id, purpose)
        return LlmAnalysisResult(
            findings=[],
            provider=self.name,
            model_version=self.model_version,
            raw_refusal=True,
            schema_valid=False,
            rejection_reason="llm_not_configured",
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
        return LlmAnalysisResult(
            findings=[],
            provider=self.name,
            model_version=self.model_version,
            raw_refusal=True,
            schema_valid=False,
            rejection_reason="llm_not_configured",
        )

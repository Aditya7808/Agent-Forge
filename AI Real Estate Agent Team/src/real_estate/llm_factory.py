"""
LLM factory — single place that knows which Agno model class to construct
for a given provider, so the pipeline stays provider-agnostic.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

from .config import LLMProvider, get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LLMHandle:
    provider: LLMProvider
    model_id: str
    instance: Any  # An Agno-compatible model instance.


def build_llm(
    provider: Optional[LLMProvider] = None,
    api_key: Optional[str] = None,
    model_id: Optional[str] = None,
) -> LLMHandle:
    """
    Construct an Agno-compatible LLM handle. Imports are lazy so the package
    works even when only one provider is installed.
    """
    settings = get_settings()
    resolved_provider: LLMProvider = provider or settings.llm_provider

    if resolved_provider == "gemini":
        from agno.models.google import Gemini

        key = api_key or settings.google_api_key
        if not key:
            raise ValueError("GOOGLE_API_KEY is required for the gemini provider.")
        mid = model_id or settings.gemini_model
        logger.info("LLM provider=gemini model=%s", mid)
        return LLMHandle("gemini", mid, Gemini(id=mid, api_key=key))

    if resolved_provider == "openai":
        from agno.models.openai import OpenAIChat

        key = api_key or settings.openai_api_key
        if not key:
            raise ValueError("OPENAI_API_KEY is required for the openai provider.")
        mid = model_id or settings.openai_model
        logger.info("LLM provider=openai model=%s", mid)
        return LLMHandle("openai", mid, OpenAIChat(id=mid, api_key=key))

    if resolved_provider == "anthropic":
        from agno.models.anthropic import Claude

        key = api_key or settings.anthropic_api_key
        if not key:
            raise ValueError("ANTHROPIC_API_KEY is required for the anthropic provider.")
        mid = model_id or settings.anthropic_model
        logger.info("LLM provider=anthropic model=%s", mid)
        return LLMHandle("anthropic", mid, Claude(id=mid, api_key=key))

    if resolved_provider == "ollama":
        from agno.models.ollama import Ollama

        mid = model_id or settings.ollama_model
        logger.info("LLM provider=ollama model=%s", mid)
        return LLMHandle("ollama", mid, Ollama(id=mid, host=settings.ollama_host))

    raise ValueError(f"Unsupported LLM provider: {resolved_provider}")

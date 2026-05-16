"""LLM wrapper — currently OpenAI Chat Completions, streaming-first."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, List, Optional

from audio_chat.config import Settings
from audio_chat.exceptions import LLMError
from audio_chat.logger import get_logger

logger = get_logger("llm")


@dataclass
class ChatMessage:
    role: str  # "system" | "user" | "assistant"
    content: str

    def to_dict(self) -> dict:
        return {"role": self.role, "content": self.content}


class OpenAIChatLLM:
    """Thin OpenAI client supporting both streaming and one-shot completions."""

    def __init__(self, settings: Settings):
        try:
            from openai import OpenAI
        except ImportError as e:
            raise LLMError(
                "openai package is required. Install with: pip install openai"
            ) from e
        if not settings.openai_api_key:
            raise LLMError("OPENAI_API_KEY is required for OpenAIChatLLM.")
        self._client = OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
        self.model = settings.llm_model
        self.temperature = settings.llm_temperature
        self.max_tokens = settings.llm_max_tokens
        logger.info(
            "OpenAIChatLLM initialized | model=%s temperature=%.2f max_tokens=%d",
            self.model, self.temperature, self.max_tokens,
        )

    def stream(
        self,
        messages: List[ChatMessage],
        *,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Iterator[str]:
        """Yield content deltas as they arrive from the API."""
        try:
            resp = self._client.chat.completions.create(
                model=self.model,
                messages=[m.to_dict() for m in messages],
                temperature=temperature if temperature is not None else self.temperature,
                max_tokens=max_tokens or self.max_tokens,
                stream=True,
            )
            for chunk in resp:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    yield delta.content
        except Exception as e:
            raise LLMError(f"OpenAI streaming failed: {e}") from e

    def complete(
        self,
        messages: List[ChatMessage],
        *,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Blocking, non-streaming completion."""
        try:
            resp = self._client.chat.completions.create(
                model=self.model,
                messages=[m.to_dict() for m in messages],
                temperature=temperature if temperature is not None else self.temperature,
                max_tokens=max_tokens or self.max_tokens,
                stream=False,
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            raise LLMError(f"OpenAI completion failed: {e}") from e


def build_llm(settings: Settings) -> OpenAIChatLLM:
    """Factory; currently only OpenAI is supported, but kept for symmetry."""
    if settings.llm_provider == "openai":
        return OpenAIChatLLM(settings)
    raise LLMError(f"Unknown LLM provider: {settings.llm_provider!r}")

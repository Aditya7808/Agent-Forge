"""Centralized configuration via environment variables.

All settings have safe defaults except API keys, which must be set explicitly
either via env vars or by passing kwargs to `Settings(...)`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Literal, Optional

from audio_chat.exceptions import ConfigurationError

TranscriptionProvider = Literal["openai", "assemblyai"]
EmbeddingProvider = Literal["openai", "huggingface"]
LLMProvider = Literal["openai"]


def _env(key: str, default: Optional[str] = None) -> Optional[str]:
    val = os.getenv(key)
    return val if val not in (None, "") else default


def _env_int(key: str, default: int) -> int:
    val = _env(key)
    if val is None:
        return default
    try:
        return int(val)
    except ValueError as e:
        raise ConfigurationError(f"{key} must be an integer, got {val!r}") from e


def _env_float(key: str, default: float) -> float:
    val = _env(key)
    if val is None:
        return default
    try:
        return float(val)
    except ValueError as e:
        raise ConfigurationError(f"{key} must be a float, got {val!r}") from e


def _env_bool(key: str, default: bool) -> bool:
    val = _env(key)
    if val is None:
        return default
    return val.lower() in ("1", "true", "yes", "on")


@dataclass
class Settings:
    """Runtime configuration for audio_chat.

    Construct directly for programmatic use, or call `Settings.from_env()`
    to populate from environment variables.
    """

    # --- LLM ---
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None  # for proxies / Azure / vLLM
    llm_provider: LLMProvider = "openai"
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.3
    llm_max_tokens: int = 1024

    # --- Embeddings ---
    embedding_provider: EmbeddingProvider = "openai"
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536  # 1536 for text-embedding-3-small, 3072 for -large
    embedding_batch_size: int = 64
    hf_embedding_model: str = "BAAI/bge-small-en-v1.5"  # only if provider=huggingface
    hf_cache_dir: str = "./hf_cache"

    # --- Transcription ---
    transcription_provider: TranscriptionProvider = "openai"
    openai_transcription_model: str = "whisper-1"
    assemblyai_api_key: Optional[str] = None
    assemblyai_speaker_labels: bool = True
    assemblyai_expected_speakers: int = 2

    # --- Vector store (Qdrant) ---
    qdrant_url: str = ":memory:"  # default to in-memory for zero-config startup
    qdrant_api_key: Optional[str] = None
    qdrant_prefer_grpc: bool = False
    qdrant_collection: str = "audio_chat_default"
    qdrant_upsert_batch_size: int = 256

    # --- RAG ---
    retrieval_top_k: int = 5
    chunk_size: int = 800
    chunk_overlap: int = 100
    max_context_chars: int = 8000

    # --- Audio upload limits ---
    max_audio_mb: int = 50
    allowed_audio_extensions: tuple = field(
        default_factory=lambda: (".mp3", ".wav", ".m4a", ".mp4", ".webm", ".ogg", ".flac")
    )

    # --- Logging ---
    log_level: str = "INFO"
    log_json: bool = False

    @classmethod
    def from_env(cls) -> "Settings":
        """Load settings from environment variables."""
        return cls(
            openai_api_key=_env("OPENAI_API_KEY"),
            openai_base_url=_env("OPENAI_BASE_URL"),
            llm_provider=_env("LLM_PROVIDER", "openai"),  # type: ignore[arg-type]
            llm_model=_env("LLM_MODEL", "gpt-4o-mini"),
            llm_temperature=_env_float("LLM_TEMPERATURE", 0.3),
            llm_max_tokens=_env_int("LLM_MAX_TOKENS", 1024),
            embedding_provider=_env("EMBEDDING_PROVIDER", "openai"),  # type: ignore[arg-type]
            embedding_model=_env("EMBEDDING_MODEL", "text-embedding-3-small"),
            embedding_dim=_env_int("EMBEDDING_DIM", 1536),
            embedding_batch_size=_env_int("EMBEDDING_BATCH_SIZE", 64),
            hf_embedding_model=_env("HF_EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5"),
            hf_cache_dir=_env("HF_CACHE_DIR", "./hf_cache"),
            transcription_provider=_env("TRANSCRIPTION_PROVIDER", "openai"),  # type: ignore[arg-type]
            openai_transcription_model=_env("OPENAI_TRANSCRIPTION_MODEL", "whisper-1"),
            assemblyai_api_key=_env("ASSEMBLYAI_API_KEY"),
            assemblyai_speaker_labels=_env_bool("ASSEMBLYAI_SPEAKER_LABELS", True),
            assemblyai_expected_speakers=_env_int("ASSEMBLYAI_EXPECTED_SPEAKERS", 2),
            qdrant_url=_env("QDRANT_URL", ":memory:"),
            qdrant_api_key=_env("QDRANT_API_KEY"),
            qdrant_prefer_grpc=_env_bool("QDRANT_PREFER_GRPC", False),
            qdrant_collection=_env("QDRANT_COLLECTION", "audio_chat_default"),
            qdrant_upsert_batch_size=_env_int("QDRANT_UPSERT_BATCH_SIZE", 256),
            retrieval_top_k=_env_int("RETRIEVAL_TOP_K", 5),
            chunk_size=_env_int("CHUNK_SIZE", 800),
            chunk_overlap=_env_int("CHUNK_OVERLAP", 100),
            max_context_chars=_env_int("MAX_CONTEXT_CHARS", 8000),
            max_audio_mb=_env_int("MAX_AUDIO_MB", 50),
            log_level=_env("LOG_LEVEL", "INFO"),
            log_json=_env_bool("LOG_JSON", False),
        )

    def validate(self) -> None:
        """Validate that required credentials are present for the selected providers."""
        if self.llm_provider == "openai" and not self.openai_api_key:
            raise ConfigurationError(
                "OPENAI_API_KEY is required when llm_provider='openai'. "
                "Set the env var or pass openai_api_key= to Settings()."
            )
        if self.embedding_provider == "openai" and not self.openai_api_key:
            raise ConfigurationError(
                "OPENAI_API_KEY is required when embedding_provider='openai'."
            )
        if self.transcription_provider == "openai" and not self.openai_api_key:
            raise ConfigurationError(
                "OPENAI_API_KEY is required when transcription_provider='openai'."
            )
        if self.transcription_provider == "assemblyai" and not self.assemblyai_api_key:
            raise ConfigurationError(
                "ASSEMBLYAI_API_KEY is required when transcription_provider='assemblyai'."
            )
        if self.chunk_overlap >= self.chunk_size:
            raise ConfigurationError(
                f"chunk_overlap ({self.chunk_overlap}) must be < chunk_size ({self.chunk_size})"
            )
        if self.retrieval_top_k < 1:
            raise ConfigurationError("retrieval_top_k must be >= 1")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached env-derived settings for app code that does not pass settings explicitly."""
    return Settings.from_env()

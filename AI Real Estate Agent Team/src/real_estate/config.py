"""
Centralized configuration & logging.

All env-driven settings live here. The rest of the package depends on
`get_settings()` rather than reading os.environ directly, so tests can
override settings cleanly and entry points stay slim.
"""

from __future__ import annotations

import logging
import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()

LLMProvider = Literal["gemini", "openai", "anthropic", "ollama"]


class Settings(BaseModel):
    """Runtime configuration loaded from environment variables."""

    google_api_key: Optional[str] = Field(default=None)
    openai_api_key: Optional[str] = Field(default=None)
    anthropic_api_key: Optional[str] = Field(default=None)
    firecrawl_api_key: Optional[str] = Field(default=None)

    llm_provider: LLMProvider = Field(default="gemini")
    gemini_model: str = Field(default="gemini-2.5-flash")
    openai_model: str = Field(default="gpt-4o-mini")
    anthropic_model: str = Field(default="claude-haiku-4-5-20251001")
    ollama_model: str = Field(default="gpt-oss:20b")
    ollama_host: str = Field(default="http://localhost:11434")

    cache_enabled: bool = Field(default=True)
    cache_ttl_seconds: int = Field(default=60 * 60 * 6)  # 6 hours
    cache_dir: Path = Field(default_factory=lambda: Path(".cache/real_estate"))

    history_db_path: Path = Field(
        default_factory=lambda: Path(".cache/real_estate/history.sqlite3")
    )

    firecrawl_timeout_s: int = Field(default=120)
    firecrawl_max_retries: int = Field(default=3)

    log_level: str = Field(default="INFO")
    log_json: bool = Field(default=False)

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            firecrawl_api_key=os.getenv("FIRECRAWL_API_KEY"),
            llm_provider=os.getenv("REAL_ESTATE_LLM_PROVIDER", "gemini"),  # type: ignore[arg-type]
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"),
            ollama_model=os.getenv("OLLAMA_MODEL", "gpt-oss:20b"),
            ollama_host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
            cache_enabled=os.getenv("REAL_ESTATE_CACHE", "1") not in ("0", "false", "False"),
            cache_ttl_seconds=int(os.getenv("REAL_ESTATE_CACHE_TTL", str(60 * 60 * 6))),
            cache_dir=Path(os.getenv("REAL_ESTATE_CACHE_DIR", ".cache/real_estate")),
            history_db_path=Path(
                os.getenv("REAL_ESTATE_HISTORY_DB", ".cache/real_estate/history.sqlite3")
            ),
            firecrawl_timeout_s=int(os.getenv("FIRECRAWL_TIMEOUT", "120")),
            firecrawl_max_retries=int(os.getenv("FIRECRAWL_MAX_RETRIES", "3")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_json=os.getenv("LOG_JSON", "0") in ("1", "true", "True"),
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_env()


def reload_settings() -> Settings:
    """Force re-read of environment (useful when Streamlit injects keys at runtime)."""
    get_settings.cache_clear()
    return get_settings()


_LOGGING_CONFIGURED = False


def configure_logging(level: Optional[str] = None, json_format: Optional[bool] = None) -> None:
    """Idempotent logging setup. Safe to call repeatedly from Streamlit reruns."""
    global _LOGGING_CONFIGURED
    if _LOGGING_CONFIGURED:
        return

    settings = get_settings()
    resolved_level = level or settings.log_level
    use_json = json_format if json_format is not None else settings.log_json

    handler = logging.StreamHandler(sys.stdout)
    if use_json:
        import json

        class JsonFormatter(logging.Formatter):
            def format(self, record: logging.LogRecord) -> str:  # noqa: D401
                payload = {
                    "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
                    "level": record.levelname,
                    "logger": record.name,
                    "msg": record.getMessage(),
                }
                if record.exc_info:
                    payload["exc"] = self.formatException(record.exc_info)
                return json.dumps(payload)

        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
                datefmt="%H:%M:%S",
            )
        )

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(resolved_level.upper())

    # Quiet noisy third-party loggers.
    for noisy in ("httpx", "httpcore", "urllib3", "openai", "anthropic"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _LOGGING_CONFIGURED = True

"""Centralized configuration loaded from environment variables / .env."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env", override=False)


def _csv(key: str, default: str) -> List[str]:
    raw = os.environ.get(key, default)
    return [s.strip() for s in raw.split(",") if s.strip()]


@dataclass
class Settings:
    openai_api_key: str = field(default_factory=lambda: os.environ.get("OPENAI_API_KEY", ""))
    openai_model: str = field(default_factory=lambda: os.environ.get("OPENAI_MODEL", "gpt-4o-mini"))
    openai_model_strong: str = field(default_factory=lambda: os.environ.get("OPENAI_MODEL_STRONG", "gpt-4o"))
    embedding_model: str = field(default_factory=lambda: os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small"))
    temperature: float = field(default_factory=lambda: float(os.environ.get("LLM_TEMPERATURE", "0")))

    clauses_path: str = field(
        default_factory=lambda: os.environ.get(
            "CLAUSES_PATH",
            str(Path(__file__).parent.parent / "data" / "clauses.json"),
        )
    )

    compliance_frameworks: List[str] = field(
        default_factory=lambda: _csv("COMPLIANCE_FRAMEWORKS", "GDPR,CCPA")
    )

    max_clause_checks: int = field(default_factory=lambda: int(os.environ.get("MAX_CLAUSE_CHECKS", "12")))

    def is_configured(self) -> bool:
        return bool(self.openai_api_key)


settings = Settings()

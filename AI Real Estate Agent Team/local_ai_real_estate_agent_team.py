"""
Local AI Real Estate Agent Team — Ollama entry point.

Thin wrapper. Runs the same multi-agent pipeline as the cloud version, but
uses an Ollama model (default: gpt-oss:20b) so no LLM API key is required.
You still need a Firecrawl API key for property extraction.

Make sure Ollama is running:
    ollama pull gpt-oss:20b
    ollama serve
"""

from __future__ import annotations

import sys
from pathlib import Path

_PACKAGE_ROOT = Path(__file__).resolve().parent / "src"
if str(_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(_PACKAGE_ROOT))

from real_estate.ui import render_app  # noqa: E402


def main() -> None:
    render_app(
        page_title="Local AI Real Estate Agent Team — Ollama",
        provider="ollama",
        require_provider_key=False,
    )


if __name__ == "__main__":
    main()

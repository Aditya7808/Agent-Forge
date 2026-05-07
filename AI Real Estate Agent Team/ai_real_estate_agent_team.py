"""
AI Real Estate Agent Team — cloud entry point.

This is a thin wrapper over `src.real_estate.ui.render_app`. It exists only
to be the runnable target for `streamlit run`. Provider/key resolution and
all rendering live in the package.

Default provider: Gemini 2.5 Flash. Set REAL_ESTATE_LLM_PROVIDER=openai or
=anthropic in your .env to switch.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow `streamlit run ai_real_estate_agent_team.py` to import the local package
# without needing an editable install.
_PACKAGE_ROOT = Path(__file__).resolve().parent / "src"
if str(_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(_PACKAGE_ROOT))

from real_estate.config import get_settings  # noqa: E402
from real_estate.ui import render_app  # noqa: E402


def main() -> None:
    settings = get_settings()
    provider = settings.llm_provider if settings.llm_provider != "ollama" else "gemini"
    page_title = {
        "gemini": "AI Real Estate Agent Team — Gemini",
        "openai": "AI Real Estate Agent Team — OpenAI",
        "anthropic": "AI Real Estate Agent Team — Anthropic",
    }.get(provider, "AI Real Estate Agent Team")

    render_app(
        page_title=page_title,
        provider=provider,
        require_provider_key=True,
    )


if __name__ == "__main__":
    main()

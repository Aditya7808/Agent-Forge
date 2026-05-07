"""
AI Real Estate Agent Team — modular core package.

Re-exports lightweight (pure-Python) classes eagerly. Heavy modules that
require `agno`, `firecrawl`, `plotly`, or `streamlit` are imported lazily
via `__getattr__` so unit tests for scoring/URL building don't need the
full optional dependency tree installed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .config import Settings, configure_logging, get_settings
from .schemas import (
    AnalysisResult,
    PropertyDetails,
    PropertyListing,
    ScoredProperty,
    SearchCriteria,
)
from .scoring import InvestmentScore, score_properties

if TYPE_CHECKING:  # pragma: no cover
    from .analytics import build_charts, compute_metrics
    from .exporters import to_csv, to_json, to_markdown
    from .firecrawl_service import FirecrawlService
    from .history import SearchHistory
    from .pipeline import RealEstatePipeline


_LAZY = {
    "RealEstatePipeline": (".pipeline", "RealEstatePipeline"),
    "FirecrawlService": (".firecrawl_service", "FirecrawlService"),
    "SearchHistory": (".history", "SearchHistory"),
    "compute_metrics": (".analytics", "compute_metrics"),
    "build_charts": (".analytics", "build_charts"),
    "to_markdown": (".exporters", "to_markdown"),
    "to_json": (".exporters", "to_json"),
    "to_csv": (".exporters", "to_csv"),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY:
        from importlib import import_module

        module_name, attr = _LAZY[name]
        module = import_module(module_name, __name__)
        value = getattr(module, attr)
        globals()[name] = value
        return value
    raise AttributeError(f"module 'real_estate' has no attribute {name!r}")


__all__ = [
    "Settings",
    "get_settings",
    "configure_logging",
    "PropertyDetails",
    "PropertyListing",
    "ScoredProperty",
    "SearchCriteria",
    "AnalysisResult",
    "InvestmentScore",
    "score_properties",
    # Lazy-loaded:
    "RealEstatePipeline",
    "FirecrawlService",
    "SearchHistory",
    "compute_metrics",
    "build_charts",
    "to_markdown",
    "to_json",
    "to_csv",
]

__version__ = "2.0.0"

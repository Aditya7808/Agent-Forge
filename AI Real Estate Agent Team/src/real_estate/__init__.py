"""
AI Real Estate Agent Team — modular core package.

Exposes the public API used by the Streamlit entry points and tests.
"""

from .config import Settings, get_settings, configure_logging
from .schemas import PropertyDetails, PropertyListing, SearchCriteria, AnalysisResult
from .pipeline import RealEstatePipeline
from .scoring import score_properties, InvestmentScore
from .analytics import compute_metrics, build_charts
from .history import SearchHistory
from .exporters import to_markdown, to_json, to_csv

__all__ = [
    "Settings",
    "get_settings",
    "configure_logging",
    "PropertyDetails",
    "PropertyListing",
    "SearchCriteria",
    "AnalysisResult",
    "RealEstatePipeline",
    "score_properties",
    "InvestmentScore",
    "compute_metrics",
    "build_charts",
    "SearchHistory",
    "to_markdown",
    "to_json",
    "to_csv",
]

__version__ = "2.0.0"

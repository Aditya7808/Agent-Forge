"""
Analytics — computed metrics + Plotly chart factories.

The pipeline emits ScoredProperty objects; this module turns them into the
numbers and visuals that power the analytics dashboard.
"""

from __future__ import annotations

import statistics
from collections import Counter
from typing import Any, Dict, List, Optional

from .schemas import ScoredProperty


def _safe_median(values: List[float]) -> Optional[float]:
    return statistics.median(values) if values else None


def _safe_mean(values: List[float]) -> Optional[float]:
    return statistics.mean(values) if values else None


def compute_metrics(scored: List[ScoredProperty]) -> Dict[str, Any]:
    """Compute summary metrics for the analytics dashboard."""
    prices = [s.price_numeric for s in scored if s.price_numeric is not None]
    ppsf = [s.price_per_sqft for s in scored if s.price_per_sqft is not None]
    sqft = [s.sqft_numeric for s in scored if s.sqft_numeric is not None]
    scores = [s.investment_score for s in scored]

    type_counts = Counter(
        (s.property.property_type or "Unknown").strip() or "Unknown" for s in scored
    )
    source_counts = Counter(
        (s.property.source_website or "Unknown").strip() or "Unknown" for s in scored
    )
    band_counts = Counter(s.investment_band for s in scored)

    in_budget_count = sum(1 for s in scored if s.in_budget)
    matches_count = sum(1 for s in scored if s.matches_criteria)

    return {
        "total_properties": len(scored),
        "in_budget_count": in_budget_count,
        "matches_criteria_count": matches_count,
        "price": {
            "min": min(prices) if prices else None,
            "max": max(prices) if prices else None,
            "median": _safe_median(prices),
            "mean": _safe_mean(prices),
        },
        "price_per_sqft": {
            "min": min(ppsf) if ppsf else None,
            "max": max(ppsf) if ppsf else None,
            "median": _safe_median(ppsf),
            "mean": _safe_mean(ppsf),
        },
        "sqft": {
            "min": min(sqft) if sqft else None,
            "max": max(sqft) if sqft else None,
            "median": _safe_median(sqft),
        },
        "investment_score": {
            "mean": _safe_mean(scores) if scores else None,
            "median": _safe_median(scores) if scores else None,
            "max": max(scores) if scores else None,
            "min": min(scores) if scores else None,
        },
        "type_breakdown": dict(type_counts),
        "source_breakdown": dict(source_counts),
        "band_breakdown": dict(band_counts),
    }


def build_charts(scored: List[ScoredProperty]) -> Dict[str, Any]:
    """
    Build Plotly figures for the analytics dashboard.

    Imported lazily so unit tests that only exercise scoring don't pull in
    plotly. Returns a dict[name -> plotly Figure]; missing charts (insufficient
    data) are simply omitted.
    """
    import plotly.express as px
    import plotly.graph_objects as go

    figures: Dict[str, Any] = {}

    # 1. Price distribution
    prices = [s.price_numeric for s in scored if s.price_numeric is not None]
    if prices:
        fig = px.histogram(
            x=prices,
            nbins=min(20, max(5, len(prices) // 2)),
            labels={"x": "Price ($)", "y": "# Listings"},
            title="Price Distribution",
        )
        fig.update_layout(showlegend=False, bargap=0.05)
        figures["price_distribution"] = fig

    # 2. Price per square foot — box per property type
    ppsf_rows = [
        (s.property.property_type or "Unknown", s.price_per_sqft)
        for s in scored
        if s.price_per_sqft is not None
    ]
    if ppsf_rows:
        types = [r[0] for r in ppsf_rows]
        values = [r[1] for r in ppsf_rows]
        fig = px.box(
            x=types,
            y=values,
            points="all",
            labels={"x": "Property Type", "y": "Price / sqft ($)"},
            title="Price per Square Foot by Property Type",
        )
        figures["ppsf_by_type"] = fig

    # 3. Property-type breakdown
    type_counts = Counter(
        (s.property.property_type or "Unknown").strip() or "Unknown" for s in scored
    )
    if type_counts:
        fig = px.pie(
            names=list(type_counts.keys()),
            values=list(type_counts.values()),
            title="Property Type Mix",
            hole=0.4,
        )
        figures["type_breakdown"] = fig

    # 4. Investment score distribution
    scores = [s.investment_score for s in scored]
    if scores:
        fig = px.histogram(
            x=scores,
            nbins=10,
            labels={"x": "Investment Score (0-100)", "y": "# Listings"},
            title="Investment Score Distribution",
            range_x=[0, 100],
        )
        fig.add_vline(
            x=75, line_dash="dash", line_color="green", annotation_text="High"
        )
        fig.add_vline(
            x=55, line_dash="dash", line_color="orange", annotation_text="Medium"
        )
        figures["score_distribution"] = fig

    # 5. Beds vs Price scatter
    pts = [
        (s.bedrooms_numeric, s.price_numeric, s.investment_score, s.property.address)
        for s in scored
        if s.bedrooms_numeric is not None and s.price_numeric is not None
    ]
    if pts:
        fig = go.Figure(
            go.Scatter(
                x=[p[0] for p in pts],
                y=[p[1] for p in pts],
                mode="markers",
                marker=dict(
                    size=10,
                    color=[p[2] for p in pts],
                    colorscale="Viridis",
                    showscale=True,
                    colorbar=dict(title="Score"),
                ),
                text=[p[3] for p in pts],
                hovertemplate="<b>%{text}</b><br>Beds: %{x}<br>Price: $%{y:,.0f}<extra></extra>",
            )
        )
        fig.update_layout(
            title="Bedrooms vs Price (color = investment score)",
            xaxis_title="Bedrooms",
            yaxis_title="Price ($)",
        )
        figures["beds_vs_price"] = fig

    # 6. Source comparison
    source_counts = Counter(
        (s.property.source_website or "Unknown").strip() or "Unknown" for s in scored
    )
    if len(source_counts) > 1:
        fig = px.bar(
            x=list(source_counts.keys()),
            y=list(source_counts.values()),
            labels={"x": "Source", "y": "# Listings"},
            title="Listings by Source",
        )
        figures["source_breakdown"] = fig

    return figures

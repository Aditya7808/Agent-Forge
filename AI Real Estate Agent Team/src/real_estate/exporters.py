"""Multi-format exporters for analysis results."""

from __future__ import annotations

import csv
import io
import json
from typing import Any, Dict

from .schemas import AnalysisResult


def _safe(value: Any, fallback: str = "Not specified") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return text or fallback


def to_markdown(result: AnalysisResult) -> str:
    """Human-readable Markdown report — matches the original output format
    while incorporating investment scores and metrics."""
    c = result.criteria
    parts: list[str] = []
    parts.append(f"# 🏠 Real Estate Analysis — {c.city}{', ' + c.state if c.state else ''}")
    parts.append(
        f"_Generated {result.timestamp.strftime('%Y-%m-%d %H:%M UTC')} • "
        f"provider: `{result.provider}` • model: `{result.model}` • "
        f"elapsed: {result.elapsed_seconds}s_"
    )
    if result.cached:
        parts.append("> Listings sourced from Firecrawl cache (TTL window).")

    parts.append("\n## Search Criteria\n")
    parts.append(f"- Budget: {c.budget_range}")
    parts.append(f"- Property type: {c.property_type}")
    parts.append(f"- Bedrooms: {c.bedrooms} | Bathrooms: {c.bathrooms}")
    parts.append(f"- Min sqft: {c.min_sqft}")
    parts.append(f"- Sources: {', '.join(c.selected_websites)}")
    if c.special_features:
        parts.append(f"- Features: {c.special_features}")

    parts.append("\n## Summary Metrics\n")
    metrics: Dict[str, Any] = result.metrics
    parts.append(f"- Total properties: {metrics.get('total_properties', 0)}")
    parts.append(f"- In budget: {metrics.get('in_budget_count', 0)}")
    parts.append(f"- Match criteria: {metrics.get('matches_criteria_count', 0)}")
    price = metrics.get("price", {})
    if price.get("median"):
        parts.append(
            f"- Price (median / mean): ${int(price['median']):,} / "
            f"${int(price.get('mean') or price['median']):,}"
        )
    ppsf = metrics.get("price_per_sqft", {})
    if ppsf.get("median"):
        parts.append(f"- Price / sqft (median): ${int(ppsf['median']):,}")

    parts.append("\n## Properties (ranked by investment score)\n")
    for i, item in enumerate(result.scored, start=1):
        p = item.property
        parts.append(f"### {i}. {_safe(p.address)}")
        parts.append(
            f"- **Price:** {_safe(p.price)} | **Score:** {item.investment_score} "
            f"({item.investment_band})"
        )
        parts.append(
            f"- **Type:** {_safe(p.property_type)} | "
            f"**Beds/Baths:** {_safe(p.bedrooms)} / {_safe(p.bathrooms)} | "
            f"**Sqft:** {_safe(p.square_feet)}"
        )
        if item.price_per_sqft:
            parts.append(f"- **Price / sqft:** ${item.price_per_sqft:,.0f}")
        if p.listing_url:
            parts.append(f"- **Listing:** [{p.listing_url}]({p.listing_url})")
        if p.description:
            parts.append(f"- {p.description}")
        parts.append("")

    parts.append("\n## Market Analysis\n")
    parts.append(result.market_analysis or "_No market analysis available._")

    parts.append("\n## Per-Property Valuations\n")
    parts.append(result.property_valuations or "_No valuations available._")

    return "\n".join(parts)


def to_json(result: AnalysisResult) -> str:
    """Serialize the full structured result for downstream tools."""
    return json.dumps(json.loads(result.model_dump_json()), indent=2, default=str)


def to_csv(result: AnalysisResult) -> str:
    """Flat CSV of scored properties — easy to import into Excel/Sheets."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "rank",
            "address",
            "price",
            "price_numeric",
            "price_per_sqft",
            "property_type",
            "bedrooms",
            "bathrooms",
            "square_feet",
            "in_budget",
            "matches_criteria",
            "investment_score",
            "investment_band",
            "source_website",
            "listing_url",
        ]
    )
    for i, item in enumerate(result.scored, start=1):
        p = item.property
        writer.writerow(
            [
                i,
                p.address,
                p.price or "",
                item.price_numeric or "",
                f"{item.price_per_sqft:.2f}" if item.price_per_sqft else "",
                p.property_type or "",
                p.bedrooms or "",
                p.bathrooms or "",
                p.square_feet or "",
                item.in_budget,
                item.matches_criteria,
                item.investment_score,
                item.investment_band,
                p.source_website or "",
                p.listing_url or "",
            ]
        )
    return buf.getvalue()

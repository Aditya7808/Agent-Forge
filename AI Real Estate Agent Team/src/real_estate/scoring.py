"""
Deterministic investment scoring.

LLM commentary is great for narrative but unreliable for ranking. This module
produces a 0..100 investment score from concrete signals (price-per-sqft vs
market median, budget fit, criteria match, listing freshness) so the UI can
sort properties consistently across runs.
"""

from __future__ import annotations

import re
import statistics
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel

from .schemas import PropertyDetails, ScoredProperty, SearchCriteria


_NUMBER_RE = re.compile(r"[\d,.]+")


class InvestmentScore(BaseModel):
    score: float
    band: str
    components: Dict[str, float]


def _parse_number(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"not specified", "n/a", "none"}:
        return None
    match = _NUMBER_RE.search(text.replace(",", ""))
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _parse_int(value: Optional[str]) -> Optional[int]:
    num = _parse_number(value)
    return int(num) if num is not None else None


def _band(score: float) -> str:
    if score >= 75:
        return "High"
    if score >= 55:
        return "Medium"
    if score >= 30:
        return "Low"
    return "Unrated"


def _budget_fit(price: Optional[float], min_p: int, max_p: int) -> Tuple[bool, float]:
    """Return (in_budget, fit_score 0..1)."""
    if price is None:
        return (True, 0.5)
    if max_p <= 0:
        return (True, 0.7)
    if price < min_p:
        # Below budget — could indicate a deal, but also could be a stale or low-quality listing.
        return (True, 0.6)
    if price <= max_p:
        # Reward properties that hit the sweet spot (~70% of max budget).
        sweet = max_p * 0.7
        delta = abs(price - sweet) / max(sweet, 1)
        return (True, max(0.5, 1.0 - min(delta, 0.5)))
    overshoot = (price - max_p) / max(max_p, 1)
    return (False, max(0.0, 0.4 - overshoot))


def _criteria_match(prop: PropertyDetails, criteria: SearchCriteria) -> Tuple[bool, float]:
    """Return (matches_hard_criteria, soft_match_score 0..1)."""
    score = 1.0
    matches = True

    if criteria.bedrooms not in {"", "Any"}:
        beds = _parse_int(prop.bedrooms)
        target = _parse_int(criteria.bedrooms.replace("+", "")) or 0
        if beds is None:
            score -= 0.2
        elif criteria.bedrooms.endswith("+"):
            if beds < target:
                matches = False
                score -= 0.3
        elif beds != target:
            score -= 0.15

    if criteria.bathrooms not in {"", "Any"}:
        baths = _parse_number(prop.bathrooms)
        target = _parse_number(criteria.bathrooms.replace("+", ""))
        if baths is None or target is None:
            score -= 0.1
        elif criteria.bathrooms.endswith("+"):
            if baths < target:
                matches = False
                score -= 0.2
        elif abs(baths - target) > 0.5:
            score -= 0.1

    if criteria.min_sqft and criteria.min_sqft > 0:
        sqft = _parse_number(prop.square_feet)
        if sqft is None:
            score -= 0.1
        elif sqft < criteria.min_sqft * 0.9:
            matches = False
            score -= 0.2

    if criteria.property_type not in {"", "Any"} and prop.property_type:
        if criteria.property_type.lower() not in (prop.property_type or "").lower():
            score -= 0.1

    return matches, max(0.0, min(score, 1.0))


def _ppsf_score(ppsf: Optional[float], median: Optional[float]) -> float:
    """Lower price-per-sqft vs market median scores higher (capped)."""
    if ppsf is None or median is None or median <= 0:
        return 0.5
    ratio = ppsf / median
    # 0.7x median → 1.0; 1.0x → 0.6; 1.3x → 0.2; 1.5x+ → 0.0
    if ratio <= 0.7:
        return 1.0
    if ratio <= 1.0:
        return 1.0 - (ratio - 0.7) * (0.4 / 0.3)
    if ratio <= 1.5:
        return max(0.0, 0.6 - (ratio - 1.0) * (0.6 / 0.5))
    return 0.0


def score_properties(
    properties: List[PropertyDetails], criteria: SearchCriteria
) -> List[ScoredProperty]:
    """Score and enrich every property with deterministic signals."""
    enriched: List[ScoredProperty] = []

    # First pass: parse numerics so we can compute a market median for ppsf.
    prelim: List[Tuple[PropertyDetails, Optional[float], Optional[float], Optional[float]]] = []
    ppsf_values: List[float] = []
    for prop in properties:
        price = _parse_number(prop.price)
        sqft = _parse_number(prop.square_feet)
        ppsf = (price / sqft) if (price and sqft and sqft > 0) else None
        if ppsf is not None and 50 <= ppsf <= 5000:  # outlier guard
            ppsf_values.append(ppsf)
        prelim.append((prop, price, sqft, ppsf))

    median_ppsf = statistics.median(ppsf_values) if ppsf_values else None

    for prop, price, sqft, ppsf in prelim:
        in_budget, budget_component = _budget_fit(price, criteria.min_price, criteria.max_price)
        matches, criteria_component = _criteria_match(prop, criteria)
        ppsf_component = _ppsf_score(ppsf, median_ppsf)
        completeness = _completeness_score(prop)

        # Weighted blend → 0..100.
        score = (
            ppsf_component * 35
            + budget_component * 25
            + criteria_component * 25
            + completeness * 15
        )

        components = {
            "price_per_sqft": round(ppsf_component, 3),
            "budget_fit": round(budget_component, 3),
            "criteria_match": round(criteria_component, 3),
            "completeness": round(completeness, 3),
        }

        enriched.append(
            ScoredProperty(
                property=prop,
                price_numeric=price,
                sqft_numeric=sqft,
                price_per_sqft=ppsf,
                bedrooms_numeric=_parse_int(prop.bedrooms),
                bathrooms_numeric=_parse_number(prop.bathrooms),
                in_budget=in_budget,
                matches_criteria=matches,
                investment_score=round(score, 1),
                investment_band=_band(score),
                score_components=components,
            )
        )

    enriched.sort(key=lambda x: x.investment_score, reverse=True)
    return enriched


def _completeness_score(prop: PropertyDetails) -> float:
    """How complete is this listing? Properties missing key fields rank lower."""
    fields = [
        prop.price,
        prop.bedrooms,
        prop.bathrooms,
        prop.square_feet,
        prop.property_type,
        prop.listing_url,
        prop.description,
    ]
    filled = sum(
        1 for v in fields if v and str(v).strip() and str(v).lower() != "not specified"
    )
    return filled / len(fields)

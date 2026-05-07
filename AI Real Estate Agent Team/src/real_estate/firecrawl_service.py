"""
Firecrawl service — scraping with retries, caching, and deterministic URL building.

Wraps the Firecrawl extract endpoint behind a small, testable surface so the
pipeline never reaches into env vars or HTTP details directly.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from firecrawl import FirecrawlApp

from .config import get_settings
from .schemas import PropertyListing, SearchCriteria

logger = logging.getLogger(__name__)


SUPPORTED_SITES = ["Zillow", "Realtor.com", "Trulia", "Homes.com"]


def build_search_urls(criteria: SearchCriteria) -> Dict[str, str]:
    """Construct site-specific search URLs from validated criteria."""
    city_dash = criteria.city.replace(" ", "-").lower()
    city_under = criteria.city.replace(" ", "_")
    state_upper = criteria.state.upper() if criteria.state else ""
    state_lower = criteria.state.lower() if criteria.state else ""

    return {
        "Zillow": f"https://www.zillow.com/homes/for_sale/{city_dash}-{state_upper}/",
        "Realtor.com": (
            f"https://www.realtor.com/realestateandhomes-search/{city_dash}_{state_upper}/pg-1"
        ),
        "Trulia": f"https://www.trulia.com/{state_upper}/{city_under}/",
        "Homes.com": f"https://www.homes.com/homes-for-sale/{city_dash}-{state_lower}/",
    }


def select_urls(criteria: SearchCriteria) -> List[str]:
    all_urls = build_search_urls(criteria)
    return [url for site, url in all_urls.items() if site in criteria.selected_websites]


def _build_extraction_prompt(criteria: SearchCriteria) -> str:
    c = criteria.to_extraction_dict()
    return f"""You are extracting property listings from real estate websites. Extract EVERY property listing visible on the page.

USER SEARCH CRITERIA:
- Budget: {c['budget_range']}
- Property Type: {c['property_type']}
- Bedrooms: {c['bedrooms']}
- Bathrooms: {c['bathrooms']}
- Min Square Feet: {c['min_sqft']}
- Special Features: {c['special_features']}

EXTRACTION INSTRUCTIONS:
1. Find ALL property listings on the page (typically 20-40 per page).
2. For EACH property, extract:
   - address (required), price (required), bedrooms, bathrooms
   - square_feet, property_type, description
   - listing_url (direct link to property detail page if available)
   - agent_contact (name and/or phone if visible)
   - source_website (Zillow/Realtor/Trulia/Homes)
3. Use "Not specified" for missing optional fields. Always fill address and price.
4. Extract AT LEAST 10 properties if they exist on the page.
5. Return JSON with `properties` (array), `total_count` (int), `source_website` (string).

EXTRACT EVERY VISIBLE PROPERTY — DO NOT LIMIT TO JUST A FEW.
"""


def _cache_key(urls: List[str], criteria: SearchCriteria) -> str:
    payload = json.dumps(
        {"urls": sorted(urls), "criteria": criteria.model_dump()},
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class FirecrawlService:
    """Resilient Firecrawl wrapper with optional file-based caching."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        settings = get_settings()
        resolved_key = api_key or settings.firecrawl_api_key
        if not resolved_key:
            raise ValueError("FIRECRAWL_API_KEY is not configured.")
        self._client = FirecrawlApp(api_key=resolved_key)
        self._settings = settings
        self._cache_dir: Path = settings.cache_dir
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, key: str) -> Path:
        return self._cache_dir / f"firecrawl_{key}.json"

    def _read_cache(self, key: str) -> Optional[Dict[str, Any]]:
        if not self._settings.cache_enabled:
            return None
        path = self._cache_path(key)
        if not path.exists():
            return None
        age = time.time() - path.stat().st_mtime
        if age > self._settings.cache_ttl_seconds:
            logger.debug("Cache expired (age=%.0fs > ttl=%ds)", age, self._settings.cache_ttl_seconds)
            return None
        try:
            with path.open("r", encoding="utf-8") as fh:
                logger.info("Firecrawl cache HIT (key=%s, age=%.0fs)", key[:8], age)
                return json.load(fh)
        except json.JSONDecodeError:
            logger.warning("Corrupt cache file %s — ignoring", path)
            return None

    def _write_cache(self, key: str, payload: Dict[str, Any]) -> None:
        if not self._settings.cache_enabled:
            return
        try:
            with self._cache_path(key).open("w", encoding="utf-8") as fh:
                json.dump(payload, fh, default=str)
        except OSError as exc:
            logger.warning("Failed to write cache: %s", exc)

    def extract_properties(self, criteria: SearchCriteria) -> Dict[str, Any]:
        """
        Run a Firecrawl extract call for the configured criteria.

        Returns a dict with one of two shapes:
          - on success: {"success": True, "properties": [...], "total_count": N,
                         "source_websites": [...], "cached": bool}
          - on failure: {"error": "<message>"}
        """
        urls = select_urls(criteria)
        if not urls:
            return {"error": "No real-estate websites selected for search."}

        key = _cache_key(urls, criteria)
        cached = self._read_cache(key)
        if cached is not None:
            cached["cached"] = True
            return cached

        prompt = _build_extraction_prompt(criteria)
        last_exc: Optional[Exception] = None

        for attempt in range(1, self._settings.firecrawl_max_retries + 1):
            try:
                logger.info(
                    "Firecrawl extract: urls=%d attempt=%d/%d",
                    len(urls),
                    attempt,
                    self._settings.firecrawl_max_retries,
                )
                raw = self._client.extract(
                    urls,
                    prompt=prompt,
                    schema=PropertyListing.model_json_schema(),
                )
                normalized = self._normalize_response(raw, criteria.selected_websites)
                if "error" not in normalized:
                    self._write_cache(key, normalized)
                return normalized
            except Exception as exc:  # noqa: BLE001 — Firecrawl raises a variety of types
                last_exc = exc
                backoff = min(2 ** (attempt - 1), 8)
                logger.warning(
                    "Firecrawl attempt %d failed: %s (retrying in %ss)", attempt, exc, backoff
                )
                time.sleep(backoff)

        return {"error": f"Firecrawl extraction failed after retries: {last_exc}"}

    @staticmethod
    def _normalize_response(raw: Any, selected_sites: List[str]) -> Dict[str, Any]:
        """Coerce the variable Firecrawl response shapes into a stable dict."""
        success = False
        data: Dict[str, Any] = {}

        if hasattr(raw, "success"):
            success = bool(raw.success)
            data = getattr(raw, "data", {}) or {}
        elif isinstance(raw, dict):
            success = bool(raw.get("success"))
            data = raw.get("data") or {}

        properties = data.get("properties", []) if isinstance(data, dict) else []
        total = data.get("total_count", len(properties)) if isinstance(data, dict) else 0

        if not properties:
            return {
                "error": (
                    f"No properties extracted (Firecrawl reported success={success}, "
                    f"total_count={total}). Try broader criteria or different sources."
                )
            }

        return {
            "success": True,
            "properties": properties,
            "total_count": len(properties),
            "source_websites": selected_sites,
            "cached": False,
        }

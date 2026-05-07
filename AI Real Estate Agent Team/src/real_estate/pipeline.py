"""
Multi-agent pipeline.

Runs in three stages: Firecrawl extraction → market analysis → per-property
valuation, with deterministic investment scoring layered on top. The pipeline
is provider-agnostic — pass any LLMHandle from `llm_factory`.
"""

from __future__ import annotations

import logging
import time
from typing import Callable, Optional

from agno.agent import Agent

from .analytics import compute_metrics
from .firecrawl_service import FirecrawlService
from .llm_factory import LLMHandle
from .prompts import (
    MARKET_ANALYSIS_INSTRUCTIONS,
    PROPERTY_SEARCH_INSTRUCTIONS,
    PROPERTY_VALUATION_INSTRUCTIONS,
    market_prompt,
    valuation_prompt,
)
from .schemas import (
    AnalysisResult,
    PropertyDetails,
    ScoredProperty,
    SearchCriteria,
)
from .scoring import score_properties

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[float, str, Optional[str]], None]


def _noop_progress(_progress: float, _status: str, _activity: Optional[str] = None) -> None:
    pass


class RealEstatePipeline:
    """Sequential, observable property-analysis pipeline."""

    def __init__(
        self,
        llm: LLMHandle,
        firecrawl: Optional[FirecrawlService] = None,
    ) -> None:
        self._llm = llm
        self._firecrawl = firecrawl or FirecrawlService()
        self._market_agent = Agent(
            name="Market Analysis Agent",
            model=llm.instance,
            instructions=MARKET_ANALYSIS_INSTRUCTIONS,
        )
        self._valuation_agent = Agent(
            name="Property Valuation Agent",
            model=llm.instance,
            instructions=PROPERTY_VALUATION_INSTRUCTIONS,
        )
        # Search agent is currently a deterministic step — kept for future use.
        self._search_agent = Agent(
            name="Property Search Agent",
            model=llm.instance,
            instructions=PROPERTY_SEARCH_INSTRUCTIONS,
        )

    def run(
        self,
        criteria: SearchCriteria,
        on_progress: ProgressCallback = _noop_progress,
    ) -> AnalysisResult:
        start = time.time()
        on_progress(0.10, "Initializing", "🚀 Starting property analysis pipeline")

        # Stage 1 — Firecrawl extraction.
        on_progress(0.20, "Searching properties", "🔍 Extracting listings via Firecrawl")
        result = self._firecrawl.extract_properties(criteria)
        if "error" in result:
            raise RuntimeError(result["error"])

        raw_properties = result.get("properties", [])
        properties = [self._coerce_property(p) for p in raw_properties]
        if not properties:
            raise RuntimeError("No properties found matching your criteria.")

        cached = bool(result.get("cached"))
        on_progress(
            0.40,
            "Properties found",
            f"✅ Extracted {len(properties)} properties"
            + (" (from cache)" if cached else ""),
        )

        # Stage 2 — Deterministic scoring (cheap, runs before LLM calls).
        scored = score_properties(properties, criteria)
        on_progress(0.50, "Scoring complete", "🧮 Investment scoring complete")

        # Stage 3 — Market analysis.
        on_progress(0.60, "Analyzing market", "📊 Running market analysis agent")
        market_analysis = self._run_market_agent(scored, criteria)

        # Stage 4 — Per-property valuation.
        on_progress(0.80, "Valuing properties", "💰 Running property valuation agent")
        property_valuations = self._run_valuation_agent(scored, criteria)

        # Stage 5 — Metrics & assembly.
        on_progress(0.95, "Synthesizing", "🧩 Building analytics dashboard")
        metrics = compute_metrics(scored)

        elapsed = time.time() - start
        on_progress(1.0, "Done", f"🎉 Analysis complete in {elapsed:.1f}s")

        return AnalysisResult(
            criteria=criteria,
            properties=properties,
            scored=scored,
            market_analysis=market_analysis,
            property_valuations=property_valuations,
            metrics=metrics,
            elapsed_seconds=round(elapsed, 2),
            cached=cached,
            provider=self._llm.provider,
            model=self._llm.model_id,
        )

    @staticmethod
    def _coerce_property(raw: object) -> PropertyDetails:
        if isinstance(raw, PropertyDetails):
            return raw
        if isinstance(raw, dict):
            try:
                return PropertyDetails.model_validate(raw)
            except Exception:  # noqa: BLE001 — accept partial dicts gracefully
                return PropertyDetails(
                    address=str(raw.get("address") or "Address not available"),
                    price=raw.get("price"),
                    bedrooms=raw.get("bedrooms"),
                    bathrooms=raw.get("bathrooms"),
                    square_feet=raw.get("square_feet"),
                    property_type=raw.get("property_type"),
                    description=raw.get("description"),
                    features=raw.get("features"),
                    images=raw.get("images"),
                    agent_contact=raw.get("agent_contact"),
                    listing_url=raw.get("listing_url"),
                    source_website=raw.get("source_website"),
                )
        # Fallback for namespace-like objects.
        return PropertyDetails(address=str(getattr(raw, "address", "Address not available")))

    def _run_market_agent(self, scored: list[ScoredProperty], criteria: SearchCriteria) -> str:
        prompt = market_prompt(
            num_properties=len(scored),
            city=criteria.city,
            state=criteria.state,
            budget=criteria.budget_range,
        )
        try:
            response = self._market_agent.run(prompt)
            return getattr(response, "content", str(response))
        except Exception as exc:  # noqa: BLE001
            logger.exception("Market analysis agent failed")
            return f"_Market analysis unavailable: {exc}_"

    def _run_valuation_agent(
        self, scored: list[ScoredProperty], criteria: SearchCriteria
    ) -> str:
        payload = []
        for i, item in enumerate(scored, start=1):
            p = item.property
            payload.append(
                {
                    "number": i,
                    "address": p.address,
                    "price": p.price,
                    "property_type": p.property_type or "Not specified",
                    "bedrooms": p.bedrooms or "Not specified",
                    "bathrooms": p.bathrooms or "Not specified",
                    "square_feet": p.square_feet or "Not specified",
                    "investment_score": item.investment_score,
                }
            )

        prompt = valuation_prompt(payload, criteria.budget_range)
        try:
            response = self._valuation_agent.run(prompt)
            return getattr(response, "content", str(response))
        except Exception as exc:  # noqa: BLE001
            logger.exception("Valuation agent failed")
            return f"_Valuation analysis unavailable: {exc}_"

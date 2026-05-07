"""Pydantic schemas — the contract between Firecrawl, agents, and the UI."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PropertyDetails(BaseModel):
    address: str = Field(description="Full property address")
    price: Optional[str] = Field(default=None, description="Property price")
    bedrooms: Optional[str] = Field(default=None, description="Number of bedrooms")
    bathrooms: Optional[str] = Field(default=None, description="Number of bathrooms")
    square_feet: Optional[str] = Field(default=None, description="Square footage")
    property_type: Optional[str] = Field(default=None, description="Type of property")
    description: Optional[str] = Field(default=None, description="Property description")
    features: Optional[List[str]] = Field(default=None, description="Property features")
    images: Optional[List[str]] = Field(default=None, description="Property image URLs")
    agent_contact: Optional[str] = Field(default=None, description="Agent contact information")
    listing_url: Optional[str] = Field(default=None, description="Original listing URL")
    source_website: Optional[str] = Field(default=None, description="Listing source")


class PropertyListing(BaseModel):
    properties: List[PropertyDetails] = Field(description="List of properties found")
    total_count: int = Field(description="Total number of properties found")
    source_website: str = Field(description="Website where properties were found")


class SearchCriteria(BaseModel):
    """Validated user search criteria — single source of truth for the pipeline."""

    city: str
    state: str = ""
    min_price: int = 0
    max_price: int = 0
    property_type: str = "Any"
    bedrooms: str = "Any"
    bathrooms: str = "Any"
    min_sqft: int = 0
    timeline: str = "Flexible"
    urgency: str = "Not urgent"
    special_features: str = ""
    selected_websites: List[str] = Field(default_factory=lambda: ["Zillow", "Realtor.com"])

    @property
    def budget_range(self) -> str:
        if self.max_price <= 0:
            return "Any"
        return f"${self.min_price:,} - ${self.max_price:,}"

    def to_extraction_dict(self) -> Dict[str, Any]:
        return {
            "budget_range": self.budget_range,
            "property_type": self.property_type,
            "bedrooms": self.bedrooms,
            "bathrooms": self.bathrooms,
            "min_sqft": self.min_sqft,
            "special_features": self.special_features or "None specified",
        }


class ScoredProperty(BaseModel):
    """A property enriched with deterministic investment scoring."""

    property: PropertyDetails
    price_numeric: Optional[float] = None
    sqft_numeric: Optional[float] = None
    price_per_sqft: Optional[float] = None
    bedrooms_numeric: Optional[int] = None
    bathrooms_numeric: Optional[float] = None
    in_budget: bool = True
    matches_criteria: bool = True
    investment_score: float = 0.0  # 0..100
    investment_band: str = "Unrated"  # High / Medium / Low / Unrated
    score_components: Dict[str, float] = Field(default_factory=dict)


class AnalysisResult(BaseModel):
    """Top-level pipeline output consumed by the UI and exporters."""

    criteria: SearchCriteria
    properties: List[PropertyDetails]
    scored: List[ScoredProperty]
    market_analysis: str
    property_valuations: str
    metrics: Dict[str, Any]
    elapsed_seconds: float
    cached: bool = False
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    provider: str = "gemini"
    model: str = ""

    @property
    def total_properties(self) -> int:
        return len(self.properties)

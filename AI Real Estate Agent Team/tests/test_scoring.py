"""Investment scoring is deterministic — exercise the key edges."""

from __future__ import annotations

from real_estate.schemas import PropertyDetails, SearchCriteria
from real_estate.scoring import score_properties


def _make(price: str, sqft: str, beds: str = "3", baths: str = "2", **extra) -> PropertyDetails:
    base = dict(
        address="100 Test St",
        price=price,
        bedrooms=beds,
        bathrooms=baths,
        square_feet=sqft,
        property_type="House",
        listing_url="https://example.com/listing",
        description="Demo listing",
    )
    base.update(extra)
    return PropertyDetails(**base)


def _criteria(**overrides) -> SearchCriteria:
    base = dict(
        city="San Francisco",
        state="CA",
        min_price=400_000,
        max_price=1_000_000,
        property_type="House",
        bedrooms="3",
        bathrooms="2",
        min_sqft=1000,
        selected_websites=["Zillow"],
    )
    base.update(overrides)
    return SearchCriteria(**base)


def test_under_market_ppsf_scores_higher_than_overpriced() -> None:
    cheap = _make("$700,000", "2000")  # $350/sqft
    expensive = _make("$1,200,000", "1500")  # $800/sqft
    scored = score_properties([cheap, expensive], _criteria())
    addresses = [s.property.price for s in scored]
    # The cheaper-per-sqft listing should rank ahead of the expensive one.
    assert scored[0].price_per_sqft is not None
    assert scored[1].price_per_sqft is not None
    assert scored[0].price_per_sqft <= scored[1].price_per_sqft
    assert scored[0].investment_score >= scored[1].investment_score
    assert addresses[0] != addresses[1]


def test_over_budget_listings_marked_in_budget_false() -> None:
    way_over = _make("$5,000,000", "2500")
    in_budget = _make("$800,000", "1800")
    scored = score_properties([way_over, in_budget], _criteria())
    by_price = {s.property.price: s for s in scored}
    assert by_price["$5,000,000"].in_budget is False
    assert by_price["$800,000"].in_budget is True


def test_missing_required_criteria_drops_match_flag() -> None:
    too_few_beds = _make("$700,000", "2000", beds="1")
    scored = score_properties([too_few_beds], _criteria(bedrooms="3+"))
    assert scored[0].matches_criteria is False


def test_score_is_bounded_0_to_100() -> None:
    listings = [
        _make("$100,000", "2000"),
        _make("$10,000,000", "200"),
        _make("$500,000", "1500"),
    ]
    scored = score_properties(listings, _criteria())
    for item in scored:
        assert 0.0 <= item.investment_score <= 100.0


def test_band_mapping() -> None:
    high = _make("$500,000", "2500")  # ~$200/sqft, sweet spot
    low = _make("$5,000,000", "1000")  # $5000/sqft, way over budget
    scored = score_properties([high, low], _criteria())
    by_price = {s.property.price: s for s in scored}
    assert by_price["$500,000"].investment_band in {"High", "Medium"}
    assert by_price["$5,000,000"].investment_band in {"Low", "Unrated"}

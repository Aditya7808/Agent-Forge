"""URL construction is deterministic and core to extraction — keep it covered."""

from __future__ import annotations

from real_estate.firecrawl_service import build_search_urls, select_urls
from real_estate.schemas import SearchCriteria


def _criteria(**overrides) -> SearchCriteria:
    base = dict(city="San Francisco", state="CA", selected_websites=["Zillow", "Trulia"])
    base.update(overrides)
    return SearchCriteria(**base)


def test_zillow_url_uses_dashes_and_uppercase_state() -> None:
    urls = build_search_urls(_criteria())
    assert urls["Zillow"] == "https://www.zillow.com/homes/for_sale/san-francisco-CA/"


def test_trulia_url_uses_underscores() -> None:
    urls = build_search_urls(_criteria())
    assert urls["Trulia"] == "https://www.trulia.com/CA/San_Francisco/"


def test_homes_url_uses_lowercase_state() -> None:
    urls = build_search_urls(_criteria())
    assert urls["Homes.com"] == "https://www.homes.com/homes-for-sale/san-francisco-ca/"


def test_select_urls_filters_to_chosen_sites() -> None:
    urls = select_urls(_criteria(selected_websites=["Zillow"]))
    assert len(urls) == 1
    assert "zillow.com" in urls[0]


def test_select_urls_handles_missing_state() -> None:
    urls = select_urls(_criteria(state="", selected_websites=["Zillow"]))
    assert urls == ["https://www.zillow.com/homes/for_sale/san-francisco-/"]


def test_budget_range_formatting() -> None:
    c = _criteria(min_price=500_000, max_price=1_500_000)
    assert c.budget_range == "$500,000 - $1,500,000"
    c_zero = _criteria(min_price=0, max_price=0)
    assert c_zero.budget_range == "Any"

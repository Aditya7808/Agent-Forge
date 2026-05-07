"""
Streamlit UI for the AI Real Estate Agent Team.

The two entry-point scripts (cloud + local) wire up an LLM provider and call
`render_app()`. All view logic lives here.
"""

from __future__ import annotations

import logging
import os
import time
from typing import List, Optional

import streamlit as st

from .analytics import build_charts
from .config import LLMProvider, configure_logging, reload_settings
from .exporters import to_csv, to_json, to_markdown
from .firecrawl_service import SUPPORTED_SITES, FirecrawlService
from .history import SearchHistory
from .llm_factory import build_llm
from .pipeline import RealEstatePipeline
from .schemas import AnalysisResult, ScoredProperty, SearchCriteria

logger = logging.getLogger(__name__)


_BAND_COLOR = {
    "High": "#10b981",
    "Medium": "#f59e0b",
    "Low": "#6b7280",
    "Unrated": "#9ca3af",
}


def _inject_css() -> None:
    st.markdown(
        """
        <style>
            .score-badge {
                display: inline-block;
                padding: 4px 12px;
                border-radius: 999px;
                color: white;
                font-weight: 600;
                font-size: 0.85em;
                margin-left: 8px;
            }
            .property-card {
                border: 1px solid #e5e7eb;
                border-radius: 12px;
                padding: 16px;
                margin-bottom: 12px;
                background: rgba(250, 250, 250, 0.5);
            }
            .small-muted { color: #6b7280; font-size: 0.85em; }
            .listing-link {
                background-color: #2563eb;
                color: white;
                padding: 6px 14px;
                border-radius: 6px;
                text-decoration: none;
                font-size: 0.9em;
                font-weight: 500;
            }
            .listing-link:hover { background-color: #1d4ed8; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _sidebar(
    provider: LLMProvider,
    require_provider_key: bool,
) -> tuple[Optional[str], Optional[str], List[str]]:
    """Render sidebar; return (provider_api_key, firecrawl_key, selected_sites)."""
    with st.sidebar:
        st.header("⚙️ Configuration")

        provider_key: Optional[str] = None
        firecrawl_key: Optional[str] = None

        with st.expander("🔑 API Keys", expanded=True):
            if require_provider_key:
                env_var, label, placeholder, help_text = {
                    "gemini": (
                        "GOOGLE_API_KEY",
                        "Google AI API Key",
                        "AIza...",
                        "https://aistudio.google.com/app/apikey",
                    ),
                    "openai": (
                        "OPENAI_API_KEY",
                        "OpenAI API Key",
                        "sk-...",
                        "https://platform.openai.com/api-keys",
                    ),
                    "anthropic": (
                        "ANTHROPIC_API_KEY",
                        "Anthropic API Key",
                        "sk-ant-...",
                        "https://console.anthropic.com/settings/keys",
                    ),
                }[provider]
                provider_key = st.text_input(
                    label,
                    value=os.getenv(env_var, ""),
                    type="password",
                    placeholder=placeholder,
                    help=f"Get your key: {help_text}",
                )
                if provider_key:
                    os.environ[env_var] = provider_key
            else:
                st.info(
                    "🤖 Local provider (Ollama). Make sure the model is pulled and the daemon is running."
                )

            firecrawl_key = st.text_input(
                "Firecrawl API Key",
                value=os.getenv("FIRECRAWL_API_KEY", ""),
                type="password",
                placeholder="fc-...",
                help="https://firecrawl.dev",
            )
            if firecrawl_key:
                os.environ["FIRECRAWL_API_KEY"] = firecrawl_key

            reload_settings()  # pick up newly-set env vars

        with st.expander("🌐 Search Sources", expanded=True):
            selected_sites = [
                site
                for site in SUPPORTED_SITES
                if st.checkbox(site, value=site in {"Zillow", "Realtor.com"}, key=f"src_{site}")
            ]
            if not selected_sites:
                st.warning("Select at least one source to search.")

        with st.expander("🤖 Pipeline", expanded=False):
            st.markdown(
                """
                **Stages**
                1. 🔍 Firecrawl extraction — structured listings (cached).
                2. 🧮 Deterministic scoring — price/sqft, budget fit, criteria match.
                3. 📊 Market analysis agent — neighborhood + outlook.
                4. 💰 Valuation agent — per-property assessment.
                """
            )

        with st.expander("⚡ Performance", expanded=False):
            cache_on = st.checkbox(
                "Use Firecrawl cache (6h TTL)",
                value=os.getenv("REAL_ESTATE_CACHE", "1") not in ("0", "false", "False"),
                help="Skip duplicate Firecrawl calls within the TTL window.",
            )
            os.environ["REAL_ESTATE_CACHE"] = "1" if cache_on else "0"
            reload_settings()

        return provider_key, firecrawl_key, selected_sites


def _render_search_form() -> Optional[dict]:
    """Render the search form. Returns the parsed dict on submit, else None."""
    st.header("Your property requirements")
    st.info("Provide location, budget, and details — agents will handle the rest.")

    with st.form("property_preferences", clear_on_submit=False):
        st.markdown("### 📍 Location & Budget")
        col1, col2 = st.columns(2)
        with col1:
            city = st.text_input("🏙️ City", placeholder="e.g., San Francisco")
            state = st.text_input("🗺️ State (optional)", placeholder="e.g., CA")
        with col2:
            min_price = st.number_input(
                "💰 Minimum price ($)", min_value=0, value=500_000, step=50_000
            )
            max_price = st.number_input(
                "💰 Maximum price ($)", min_value=0, value=1_500_000, step=50_000
            )

        st.markdown("### 🏡 Property Details")
        col1, col2, col3 = st.columns(3)
        with col1:
            property_type = st.selectbox(
                "🏠 Type", ["Any", "House", "Condo", "Townhouse", "Apartment"]
            )
            bedrooms = st.selectbox("🛏️ Bedrooms", ["Any", "1", "2", "3", "4", "5+"])
        with col2:
            bathrooms = st.selectbox(
                "🚿 Bathrooms", ["Any", "1", "1.5", "2", "2.5", "3", "3.5", "4+"]
            )
            min_sqft = st.number_input(
                "📏 Minimum sqft", min_value=0, value=1_000, step=100
            )
        with col3:
            timeline = st.selectbox(
                "⏰ Timeline", ["Flexible", "1-3 months", "3-6 months", "6+ months"]
            )
            urgency = st.selectbox(
                "🚨 Urgency", ["Not urgent", "Somewhat urgent", "Very urgent"]
            )

        st.markdown("### ✨ Special Features")
        special_features = st.text_area(
            "🎯 Features & requirements",
            placeholder="e.g., Parking, Yard, Near transit, Good schools...",
        )

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            submitted = st.form_submit_button(
                "🚀 Start Property Analysis", type="primary", use_container_width=True
            )

    if not submitted:
        return None
    return {
        "city": city.strip(),
        "state": state.strip(),
        "min_price": int(min_price),
        "max_price": int(max_price),
        "property_type": property_type,
        "bedrooms": bedrooms,
        "bathrooms": bathrooms,
        "min_sqft": int(min_sqft),
        "timeline": timeline,
        "urgency": urgency,
        "special_features": special_features.strip(),
    }


def _band_badge(band: str) -> str:
    color = _BAND_COLOR.get(band, "#6b7280")
    return (
        f'<span class="score-badge" style="background-color:{color};">{band}</span>'
    )


def _render_property_card(rank: int, item: ScoredProperty) -> None:
    p = item.property
    with st.container():
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader(f"#{rank} 🏠 {p.address}")
            st.markdown(
                f"**Score:** {item.investment_score} {_band_badge(item.investment_band)}",
                unsafe_allow_html=True,
            )
        with col2:
            st.metric("Price", p.price or "—")
            if item.price_per_sqft:
                st.caption(f"${item.price_per_sqft:,.0f}/sqft")

        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            st.markdown(f"**Type:** {p.property_type or '—'}")
            st.markdown(
                f"**Beds/Baths:** {p.bedrooms or '—'} / {p.bathrooms or '—'}"
            )
            st.markdown(f"**Sqft:** {p.square_feet or '—'}")
            badges = []
            if not item.in_budget:
                badges.append("⚠️ over budget")
            if not item.matches_criteria:
                badges.append("⚠️ partial criteria match")
            if badges:
                st.caption(" • ".join(badges))
        with col2:
            with st.expander("🧮 Score breakdown"):
                for label, value in item.score_components.items():
                    st.progress(min(max(value, 0.0), 1.0), text=f"{label}: {value:.2f}")
        with col3:
            if p.listing_url:
                st.markdown(
                    f'<a href="{p.listing_url}" target="_blank" class="listing-link">View Listing →</a>',
                    unsafe_allow_html=True,
                )
        if p.description:
            st.caption(p.description)
        st.divider()


def _render_results(result: AnalysisResult) -> None:
    metrics = result.metrics

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Properties", metrics.get("total_properties", 0))
    median_price = metrics.get("price", {}).get("median")
    col2.metric(
        "Median price",
        f"${int(median_price):,}" if median_price else "—",
    )
    median_ppsf = metrics.get("price_per_sqft", {}).get("median")
    col3.metric(
        "Median $/sqft",
        f"${int(median_ppsf):,}" if median_ppsf else "—",
    )
    avg_score = metrics.get("investment_score", {}).get("mean")
    col4.metric(
        "Avg score",
        f"{avg_score:.1f}" if avg_score else "—",
    )

    if result.cached:
        st.caption("📦 Listings served from Firecrawl cache.")

    tab_props, tab_analytics, tab_market, tab_compare, tab_export = st.tabs(
        ["🏠 Properties", "📊 Analytics", "📈 Market & Valuation", "🆚 Compare", "📥 Export"]
    )

    with tab_props:
        scored = result.scored
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            sort_mode = st.selectbox(
                "Sort by",
                ["Investment score", "Price (low→high)", "Price (high→low)", "Sqft"],
            )
        with col2:
            band_filter = st.multiselect(
                "Investment band",
                ["High", "Medium", "Low", "Unrated"],
                default=["High", "Medium", "Low", "Unrated"],
            )
        with col3:
            in_budget_only = st.checkbox("In-budget only", value=False)

        filtered = [
            s for s in scored
            if s.investment_band in band_filter and (not in_budget_only or s.in_budget)
        ]
        if sort_mode == "Price (low→high)":
            filtered.sort(key=lambda s: s.price_numeric or float("inf"))
        elif sort_mode == "Price (high→low)":
            filtered.sort(key=lambda s: s.price_numeric or 0, reverse=True)
        elif sort_mode == "Sqft":
            filtered.sort(key=lambda s: s.sqft_numeric or 0, reverse=True)

        if not filtered:
            st.info("No properties match the current filters.")
        for i, item in enumerate(filtered, start=1):
            _render_property_card(i, item)

    with tab_analytics:
        figures = build_charts(result.scored)
        if not figures:
            st.info("Not enough data to render analytics.")
        else:
            chart_order = [
                "price_distribution",
                "ppsf_by_type",
                "type_breakdown",
                "score_distribution",
                "beds_vs_price",
                "source_breakdown",
            ]
            cols = st.columns(2)
            for i, name in enumerate(c for c in chart_order if c in figures):
                with cols[i % 2]:
                    st.plotly_chart(figures[name], use_container_width=True)

        with st.expander("Raw metrics"):
            st.json(result.metrics)

    with tab_market:
        st.subheader("📊 Market Analysis")
        st.markdown(result.market_analysis or "_No market analysis available._")
        st.divider()
        st.subheader("💰 Per-Property Valuations")
        st.markdown(result.property_valuations or "_No valuations available._")

    with tab_compare:
        addresses = [s.property.address for s in result.scored]
        chosen = st.multiselect(
            "Pick up to 4 properties to compare",
            addresses,
            max_selections=4,
        )
        if not chosen:
            st.info("Select properties above to see a side-by-side comparison.")
        else:
            picked = [s for s in result.scored if s.property.address in chosen]
            cols = st.columns(len(picked))
            for col, item in zip(cols, picked):
                with col:
                    p = item.property
                    st.markdown(f"### {p.address}")
                    st.markdown(
                        f"**Score:** {item.investment_score} ({item.investment_band})"
                    )
                    st.markdown(f"**Price:** {p.price or '—'}")
                    if item.price_per_sqft:
                        st.markdown(f"**$/sqft:** ${item.price_per_sqft:,.0f}")
                    st.markdown(f"**Type:** {p.property_type or '—'}")
                    st.markdown(
                        f"**Beds/Baths:** {p.bedrooms or '—'} / {p.bathrooms or '—'}"
                    )
                    st.markdown(f"**Sqft:** {p.square_feet or '—'}")
                    if p.listing_url:
                        st.markdown(f"[Listing →]({p.listing_url})")

    with tab_export:
        st.markdown("Download the analysis in your preferred format.")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.download_button(
                "📄 Markdown",
                data=to_markdown(result),
                file_name=f"real_estate_{result.criteria.city}_{int(time.time())}.md",
                mime="text/markdown",
                use_container_width=True,
            )
        with col2:
            st.download_button(
                "🧾 JSON",
                data=to_json(result),
                file_name=f"real_estate_{result.criteria.city}_{int(time.time())}.json",
                mime="application/json",
                use_container_width=True,
            )
        with col3:
            st.download_button(
                "📊 CSV",
                data=to_csv(result),
                file_name=f"real_estate_{result.criteria.city}_{int(time.time())}.csv",
                mime="text/csv",
                use_container_width=True,
            )


def _render_history(history: SearchHistory) -> None:
    rows = history.list_recent(limit=25)
    if not rows:
        st.info("No saved searches yet. Run an analysis — it'll be saved automatically.")
        return

    for row in rows:
        col1, col2, col3 = st.columns([6, 1, 1])
        col1.markdown(SearchHistory.format_summary(row))
        if col2.button("Reload", key=f"reload_{row['id']}"):
            saved = history.load(int(row["id"]))
            if saved:
                st.session_state["analysis_result"] = saved
                st.rerun()
            else:
                st.error("Failed to reload that saved search.")
        if col3.button("🗑️", key=f"del_{row['id']}"):
            history.delete(int(row["id"]))
            st.rerun()


def render_app(
    *,
    page_title: str = "AI Real Estate Agent Team",
    provider: LLMProvider = "gemini",
    require_provider_key: bool = True,
) -> None:
    """Main Streamlit entry point. Called by `ai_real_estate_agent_team.py`."""
    configure_logging()

    st.set_page_config(
        page_title=page_title,
        page_icon="🏠",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _inject_css()
    st.title(f"🏠 {page_title}")
    st.caption("Find your dream home with a specialized multi-agent team — backed by real analytics.")

    history = SearchHistory()

    provider_key, firecrawl_key, selected_sites = _sidebar(provider, require_provider_key)
    page = st.sidebar.radio("Page", ["🔎 Search", "📜 History"], horizontal=True)

    if page == "📜 History":
        _render_history(history)
        return

    submission = _render_search_form()

    # If we just reloaded a saved search, render it.
    if submission is None and "analysis_result" in st.session_state and not st.session_state.get("_just_ran"):
        st.success("Loaded saved analysis from history.")
        _render_results(st.session_state["analysis_result"])
        return

    if submission is None:
        return

    missing: list[str] = []
    if require_provider_key and not provider_key:
        missing.append(f"{provider} API key")
    if not firecrawl_key:
        missing.append("Firecrawl API key")
    if not submission["city"]:
        missing.append("City")
    if not selected_sites:
        missing.append("At least one source website")
    if missing:
        st.error("⚠️ Missing inputs: " + ", ".join(missing))
        return

    criteria = SearchCriteria(
        city=submission["city"],
        state=submission["state"],
        min_price=submission["min_price"],
        max_price=submission["max_price"],
        property_type=submission["property_type"],
        bedrooms=submission["bedrooms"],
        bathrooms=submission["bathrooms"],
        min_sqft=submission["min_sqft"],
        timeline=submission["timeline"],
        urgency=submission["urgency"],
        special_features=submission["special_features"],
        selected_websites=selected_sites,
    )

    progress = st.progress(0.0)
    activity = st.empty()

    def on_progress(value: float, _status: str, message: Optional[str] = None) -> None:
        progress.progress(min(max(value, 0.0), 1.0))
        if message:
            activity.info(message)

    try:
        llm = build_llm(provider=provider, api_key=provider_key)
        firecrawl = FirecrawlService(api_key=firecrawl_key)
        pipeline = RealEstatePipeline(llm=llm, firecrawl=firecrawl)
        result = pipeline.run(criteria, on_progress=on_progress)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Pipeline failed")
        st.error(f"❌ Analysis failed: {exc}")
        return
    finally:
        progress.empty()
        activity.empty()

    try:
        history.save(result)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to persist history: %s", exc)

    st.session_state["analysis_result"] = result
    st.session_state["_just_ran"] = True
    st.success(
        f"✅ Analyzed {result.total_properties} properties in {result.elapsed_seconds}s "
        f"using {result.provider} ({result.model})."
    )
    _render_results(result)

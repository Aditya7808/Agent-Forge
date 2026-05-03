"""Sidebar: configuration and run controls."""
from __future__ import annotations

import os

import streamlit as st

from config import settings


def render_sidebar() -> dict:
    st.sidebar.title("ClauseAI")
    st.sidebar.caption("Industry-grade contract analysis · LangGraph + OpenAI")

    with st.sidebar.expander("OpenAI Configuration", expanded=not settings.is_configured()):
        key = st.text_input(
            "OPENAI_API_KEY",
            value=settings.openai_api_key,
            type="password",
            help="Stored in session only. Use a .env file for persistence.",
        )
        if key and key != settings.openai_api_key:
            os.environ["OPENAI_API_KEY"] = key
            settings.openai_api_key = key
            st.sidebar.success("Key set for this session.")

        settings.openai_model = st.selectbox(
            "Primary model",
            ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1"],
            index=["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1"].index(settings.openai_model)
            if settings.openai_model in ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1"] else 0,
            help="Used for most nodes. Cheaper models work well for extraction.",
        )
        settings.openai_model_strong = st.selectbox(
            "Strong model (compliance + conflicts)",
            ["gpt-4o", "gpt-4.1", "gpt-4o-mini"],
            index=0 if settings.openai_model_strong == "gpt-4o" else
                  (1 if settings.openai_model_strong == "gpt-4.1" else 2),
        )
        settings.temperature = st.slider("Temperature", 0.0, 1.0, settings.temperature, 0.05)

    with st.sidebar.expander("Analysis Options", expanded=True):
        frameworks = st.multiselect(
            "Compliance frameworks",
            ["GDPR", "CCPA", "HIPAA", "SOX", "PCI-DSS", "ISO 27001"],
            default=settings.compliance_frameworks,
        )
        settings.compliance_frameworks = frameworks or ["GDPR"]

        settings.max_clause_checks = st.slider(
            "Max parallel clause checks", 4, 24, settings.max_clause_checks, 1,
            help="Higher = more thorough but more API calls.",
        )

    st.sidebar.markdown("---")
    st.sidebar.caption(
        f"Library: `{settings.clauses_path}`"
    )

    return {
        "ready": settings.is_configured(),
    }

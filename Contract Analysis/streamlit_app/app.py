"""ClauseAI — Streamlit entrypoint.

Run:
    streamlit run app.py
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

# Ensure local imports work regardless of how Streamlit is invoked.
ROOT = Path(__file__).parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from config import settings  # noqa: E402
from core.graph import run_analysis  # noqa: E402
from ui.sidebar import render_sidebar  # noqa: E402
from ui.views import (  # noqa: E402
    render_chat,
    render_compliance,
    render_dashboard,
    render_entities,
    render_export,
    render_modifications,
    render_report,
    render_upload,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")

st.set_page_config(
    page_title="ClauseAI · Contract Analysis",
    page_icon="📜",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _init_state():
    st.session_state.setdefault("input_state", {})
    st.session_state.setdefault("result", None)
    st.session_state.setdefault("progress_log", [])


def _progress_callback(event: dict):
    st.session_state.progress_log.append(event)


def _run(input_state: dict):
    if not settings.is_configured():
        st.error("Set your OPENAI_API_KEY in the sidebar first.")
        return None
    if not input_state.get("contract_text"):
        st.error("Upload a contract or load the sample first.")
        return None

    st.session_state.progress_log = []
    progress_box = st.empty()
    status = st.status("Running analysis…", expanded=True)

    def cb(evt: dict):
        st.session_state.progress_log.append(evt)
        with status:
            stage = evt.get("stage", "")
            msg = evt.get("message", "")
            st.write(f"**{stage}** — {msg}")

    try:
        result = run_analysis(
            contract_text=input_state["contract_text"],
            primary_objective=input_state.get("primary_objective", ""),
            specific_focus=input_state.get("specific_focus", ""),
            settings=settings,
            progress_cb=cb,
        )
        status.update(label="Analysis complete", state="complete")
        return result
    except Exception as e:
        logging.exception("Analysis failed")
        status.update(label=f"Failed: {e}", state="error")
        st.exception(e)
        return None


def main():
    _init_state()
    render_sidebar()

    st.title("📜 ClauseAI — Contract Analysis")
    st.caption("Multi-agent contract review · LangGraph + OpenAI · risk · compliance · redline · Q&A")

    tabs = st.tabs([
        "📤 Upload",
        "🚀 Run",
        "📊 Dashboard",
        "🧾 Entities",
        "📝 Modifications",
        "✅ Compliance & Gaps",
        "📄 Report",
        "💬 Chat",
        "⬇️ Export",
    ])

    with tabs[0]:
        render_upload(st.session_state.input_state)

    with tabs[1]:
        st.subheader("Run analysis")
        st.write("Use the controls below to start a full analysis.")

        c1, c2, c3 = st.columns([1, 1, 2])
        with c1:
            run_btn = st.button("▶ Run analysis", type="primary", use_container_width=True)
        with c2:
            if st.button("Reset", use_container_width=True):
                st.session_state.result = None
                st.session_state.progress_log = []
                st.rerun()
        with c3:
            if st.session_state.result:
                tele = st.session_state.result.get("telemetry", {})
                st.caption(
                    f"Last run · {tele.get('elapsed_seconds')}s · "
                    f"{tele.get('total_tokens', 0):,} tokens · "
                    f"~${tele.get('total_cost_usd', 0):.4f}"
                )

        if run_btn:
            with st.spinner("Analyzing…"):
                st.session_state.result = _run(st.session_state.input_state)

        if st.session_state.progress_log:
            with st.expander("Progress log", expanded=False):
                for evt in st.session_state.progress_log:
                    st.write(f"`{evt.get('stage','')}`  {evt.get('message','')}")

    result = st.session_state.result

    with tabs[2]:
        render_dashboard(result or {})
    with tabs[3]:
        render_entities(result or {})
    with tabs[4]:
        render_modifications(result or {})
    with tabs[5]:
        render_compliance(result or {})
    with tabs[6]:
        render_report(result or {})
    with tabs[7]:
        render_chat(result or {}, settings)
    with tabs[8]:
        render_export(result or {})


if __name__ == "__main__":
    main()

"""Tab views: Upload, Dashboard, Report, Modifications, Compliance, Chat, Export."""
from __future__ import annotations

import json
from typing import Any, Dict, List

import pandas as pd
import streamlit as st

from core import load_contract_bytes
from core.chat import answer as chat_answer
from core.exporters import redlined_docx_bytes, report_docx_bytes, report_json_bytes
from .components import compliance_chart, metric_row, risk_badge, risk_distribution_chart


SAMPLE_CONTRACT = """EMPLOYMENT AGREEMENT

This Employment Agreement (\"Agreement\") is entered into as of January 15, 2026, by and between
Acme Robotics, Inc., a Delaware corporation with offices at 100 Market St, San Francisco, CA 94105 (\"Employer\"),
and Jane Doe, residing at 22 Oak Ave, San Francisco, CA 94110, SSN 123-45-6789 (\"Employee\").

1. Position and Duties
1.1 Employee shall serve as Senior Software Engineer reporting to the VP of Engineering.
1.2 Employee shall devote her full business time and attention to the duties of her position.

2. Compensation
2.1 Base Salary: Employer shall pay Employee an annual base salary of $185,000, payable bi-weekly.
2.2 Bonus: Employee may receive a discretionary annual bonus targeted at 15% of base salary.
2.3 Equity: Employee shall receive 8,000 RSUs vesting over four years, 25% after one year and the remainder monthly.

3. Term and Termination
3.1 Employment is at-will. Either party may terminate at any time, for any reason, without notice.
3.2 Upon termination, Employee shall receive accrued but unpaid wages.

4. Non-Compete
4.1 For a period of three (3) years following termination, Employee shall not, anywhere in the world,
engage in any business that competes with Employer in any capacity whatsoever.

5. Intellectual Property
5.1 All inventions, works, and developments created by Employee during employment, whether or not related
to Employer's business, and whether created on or off Employer premises, shall be the sole property of Employer.

6. Confidentiality
6.1 Employee shall hold Employer's confidential information in strict confidence indefinitely.

7. Data Processing
7.1 Employer may collect, store, and process Employee personal data including biometric data and health records
for any business purpose, and may share such data with third parties at its discretion.

8. Governing Law
8.1 This Agreement shall be governed by the laws of the State of California.

9. Entire Agreement
9.1 This Agreement constitutes the entire agreement between the parties.
"""


# ----------------------------- Upload --------------------------------


def render_upload(state: Dict[str, Any]):
    st.subheader("1. Upload contract")
    col1, col2 = st.columns([3, 1])
    with col1:
        uploaded = st.file_uploader(
            "Drop a .pdf, .docx, .txt, or .md", type=["pdf", "docx", "txt", "md"]
        )
        if uploaded:
            try:
                state["contract_text"] = load_contract_bytes(uploaded.name, uploaded.read())
                state["contract_filename"] = uploaded.name
                st.success(f"Loaded {uploaded.name} — {len(state['contract_text']):,} chars")
            except Exception as e:
                st.error(f"Could not parse: {e}")
    with col2:
        if st.button("Use sample contract", use_container_width=True):
            state["contract_text"] = SAMPLE_CONTRACT
            state["contract_filename"] = "sample_employment_agreement.txt"
            st.success("Sample loaded.")

    if state.get("contract_text"):
        with st.expander("Preview contract text", expanded=False):
            st.text_area(
                "Contract", state["contract_text"], height=260, label_visibility="collapsed"
            )

    st.subheader("2. Review goals")
    state["primary_objective"] = st.text_input(
        "Primary objective",
        value=state.get(
            "primary_objective",
            "Identify high-risk clauses, ensure compliance, and propose negotiation points.",
        ),
    )
    state["specific_focus"] = st.text_input(
        "Specific focus (optional)",
        value=state.get("specific_focus", ""),
        placeholder="e.g. non-compete enforceability, IP scope, data privacy",
    )


# ----------------------------- Dashboard --------------------------------


def render_dashboard(result: Dict[str, Any]):
    info = result.get("contract_info")
    if not info:
        st.info("Run an analysis to see the dashboard.")
        return

    risk_score = result.get("overall_risk_score", 0)
    risk_level = result.get("overall_risk_level", "Low")

    metric_row([
        {"label": "Type", "value": info.contract_type},
        {"label": "Industry", "value": info.industry or "—"},
        {"label": "Overall risk", "value": f"{risk_level} ({risk_score})"},
        {"label": "Risk findings", "value": len(result.get("risk_findings", []))},
        {"label": "Modifications", "value": len(result.get("modifications", []))},
    ])

    tele = result.get("telemetry", {})
    if tele:
        st.caption(
            f"⏱ {tele.get('elapsed_seconds')}s · "
            f"{tele.get('total_tokens'):,} tokens · "
            f"~${tele.get('total_cost_usd'):.4f}"
        )

    st.markdown("### Executive summary")
    st.write(info.summary or "_No summary generated._")
    st.markdown(
        f"**Parties:** {', '.join(info.parties) if info.parties else '—'}  ·  "
        f"**Governing law:** {info.governing_law or '—'}  ·  "
        f"**Effective date:** {info.effective_date or '—'}"
    )

    col1, col2 = st.columns(2)
    with col1:
        risks = [r.model_dump() for r in result.get("risk_findings", [])]
        risk_distribution_chart(risks)
    with col2:
        compliance = [c.model_dump() for c in result.get("compliance_findings", [])]
        compliance_chart(compliance)

    # Top-N risks
    st.markdown("### Top risk findings")
    risks_sorted = sorted(
        result.get("risk_findings", []),
        key=lambda r: -{"Critical": 4, "High": 3, "Medium": 2, "Low": 1, "Info": 0}.get(r.risk_level, 0),
    )[:8]
    if not risks_sorted:
        st.info("No risk findings.")
    for r in risks_sorted:
        with st.container(border=True):
            cols = st.columns([1, 5, 1])
            cols[0].markdown(risk_badge(r.risk_level), unsafe_allow_html=True)
            cols[1].markdown(f"**{r.title}**  \n{r.description}")
            cols[2].caption(f"Confidence {r.confidence:.0%}")
            if r.recommendation:
                st.caption(f"💡 {r.recommendation}")


# ----------------------------- Modifications --------------------------------


def render_modifications(result: Dict[str, Any]):
    mods = result.get("modifications", [])
    if not mods:
        st.info("No suggested modifications. Run an analysis first.")
        return

    df = pd.DataFrame([m.model_dump() for m in mods])
    levels = ["Critical", "High", "Medium", "Low", "Info"]
    sel_levels = st.multiselect("Filter by risk level", levels, default=levels)
    df = df[df["risk_level"].isin(sel_levels)]
    st.caption(f"Showing {len(df)} modifications")
    for _, m in df.iterrows():
        with st.container(border=True):
            cols = st.columns([1, 6])
            cols[0].markdown(risk_badge(m.risk_level), unsafe_allow_html=True)
            cols[1].markdown(f"**Reason:** {m.reason}")
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Original**")
                st.code(m.original_text or "(insert as new text)", language="text")
            with c2:
                st.markdown("**Suggested**")
                st.code(m.suggested_text, language="text")


# ----------------------------- Compliance + missing + conflicts ---------------


def render_compliance(result: Dict[str, Any]):
    findings = result.get("compliance_findings", [])
    missing = result.get("missing_clauses", [])
    conflicts = result.get("conflicts", [])
    pii = result.get("pii_findings", [])

    st.markdown("### Compliance findings")
    if findings:
        df = pd.DataFrame([f.model_dump() for f in findings])
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No compliance findings.")

    st.markdown("### Missing or weak clauses")
    if missing:
        for m in missing:
            with st.container(border=True):
                cols = st.columns([1, 6])
                cols[0].markdown(risk_badge(m.importance), unsafe_allow_html=True)
                cols[1].markdown(f"**{m.clause_title}** — {m.why_missing_matters}")
                with st.expander("Suggested clause text"):
                    st.code(m.suggested_text, language="text")
    else:
        st.info("No missing clauses identified.")

    st.markdown("### Internal conflicts")
    if conflicts:
        for c in conflicts:
            with st.container(border=True):
                cols = st.columns([1, 6])
                cols[0].markdown(risk_badge(c.risk_level), unsafe_allow_html=True)
                cols[1].markdown(
                    f"**{c.section_a} ↔ {c.section_b}**  \n{c.description}  \n"
                    f"_Resolution: {c.resolution}_"
                )
    else:
        st.info("No conflicts detected.")

    st.markdown("### PII / sensitive data")
    if pii:
        for p in pii:
            with st.container(border=True):
                st.markdown(
                    f"**{p.type}**: `{p.excerpt[:80]}…`  \n_Recommendation: {p.recommendation}_"
                )
    else:
        st.info("No PII flagged.")


# ----------------------------- Entities --------------------------------


def render_entities(result: Dict[str, Any]):
    ent = result.get("entities")
    if not ent:
        st.info("Run an analysis first.")
        return
    e = ent.model_dump()
    cols = st.columns(2)
    with cols[0]:
        st.markdown("**Parties**")
        st.dataframe(pd.DataFrame(e["parties"]), use_container_width=True, hide_index=True)
        st.markdown("**Key dates**")
        st.dataframe(pd.DataFrame(e["key_dates"]), use_container_width=True, hide_index=True)
    with cols[1]:
        st.markdown("**Financial terms**")
        st.dataframe(pd.DataFrame(e["financial_terms"]), use_container_width=True, hide_index=True)
        st.markdown("**Obligations**")
        st.dataframe(pd.DataFrame(e["obligations"]), use_container_width=True, hide_index=True)


# ----------------------------- Report --------------------------------


def render_report(result: Dict[str, Any]):
    md = result.get("final_report_md")
    if not md:
        st.info("Run an analysis first.")
        return
    st.markdown(md)


# ----------------------------- Q&A Chat --------------------------------


def render_chat(result: Dict[str, Any], settings):
    if not result or not result.get("final_report_json"):
        st.info("Run an analysis first to chat about the contract.")
        return

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_input = st.chat_input("Ask anything about the contract or analysis…")
    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)
        with st.chat_message("assistant"):
            with st.spinner("Thinking…"):
                response = chat_answer(
                    model=settings.openai_model,
                    temperature=settings.temperature,
                    contract_text=result.get("contract_text", ""),
                    analysis_json=result.get("final_report_json", {}),
                    history=st.session_state.chat_history[:-1],
                    user_message=user_input,
                )
            st.markdown(response)
        st.session_state.chat_history.append({"role": "assistant", "content": response})

    if st.button("Clear chat", type="secondary"):
        st.session_state.chat_history = []
        st.rerun()


# ----------------------------- Export --------------------------------


def render_export(result: Dict[str, Any]):
    if not result.get("final_report_json"):
        st.info("Run an analysis first.")
        return

    st.markdown("### Downloads")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.download_button(
            "📄 Report (Markdown)",
            data=result["final_report_md"].encode("utf-8"),
            file_name="contract_report.md",
            mime="text/markdown",
            use_container_width=True,
        )
    with col2:
        st.download_button(
            "🧾 Report (JSON)",
            data=report_json_bytes(result["final_report_json"]),
            file_name="contract_report.json",
            mime="application/json",
            use_container_width=True,
        )
    with col3:
        st.download_button(
            "📑 Report (DOCX)",
            data=report_docx_bytes(result["final_report_md"]),
            file_name="contract_report.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )
    with col4:
        st.download_button(
            "✏️ Redlined contract (DOCX)",
            data=redlined_docx_bytes(
                result.get("contract_text", ""),
                result.get("modifications", []),
            ),
            file_name="redlined_contract.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )

    with st.expander("Raw analysis JSON"):
        st.json(result["final_report_json"])

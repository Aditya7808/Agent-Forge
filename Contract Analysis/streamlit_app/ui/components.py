"""Shared UI components."""
from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd
import plotly.express as px
import streamlit as st

RISK_COLORS = {
    "Critical": "#b00020",
    "High": "#d35400",
    "Medium": "#e0a800",
    "Low": "#1f8a4c",
    "Info": "#5d6d7e",
    "Compliant": "#1f8a4c",
    "Partial": "#e0a800",
    "Non-Compliant": "#b00020",
    "Not Applicable": "#5d6d7e",
}


def risk_badge(level: str) -> str:
    color = RISK_COLORS.get(level, "#555")
    return (
        f"<span style='background:{color};color:white;padding:2px 8px;"
        f"border-radius:10px;font-size:0.75rem;font-weight:600;'>{level}</span>"
    )


def metric_row(metrics: List[Dict[str, Any]]):
    cols = st.columns(len(metrics))
    for col, m in zip(cols, metrics):
        col.metric(m["label"], m["value"], delta=m.get("delta"))


def risk_distribution_chart(risks: List[Dict[str, Any]]):
    if not risks:
        st.info("No risk findings to chart.")
        return
    df = pd.DataFrame(risks)
    counts = df.groupby(["risk_level", "category"]).size().reset_index(name="count")
    fig = px.bar(
        counts,
        x="risk_level", y="count", color="category",
        category_orders={"risk_level": ["Critical", "High", "Medium", "Low", "Info"]},
        title="Risk findings by level and category",
    )
    fig.update_layout(height=320, margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig, use_container_width=True)


def compliance_chart(findings: List[Dict[str, Any]]):
    if not findings:
        st.info("No compliance findings to chart.")
        return
    df = pd.DataFrame(findings)
    counts = df.groupby(["framework", "status"]).size().reset_index(name="count")
    fig = px.bar(
        counts, x="framework", y="count", color="status",
        title="Compliance status by framework",
        color_discrete_map=RISK_COLORS,
    )
    fig.update_layout(height=320, margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig, use_container_width=True)

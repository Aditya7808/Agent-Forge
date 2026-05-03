"""Final report generator — emits both structured JSON and a Markdown executive summary."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from .state import (
    ComplianceFinding,
    Conflict,
    ContractInfo,
    EntityExtraction,
    MissingClause,
    Modification,
    PIIFinding,
    RISK_WEIGHTS,
    RiskFinding,
    StepAnalysis,
)


def _fmt_list(items: List[Any], fmt) -> str:
    return "\n".join(fmt(i) for i in items) if items else "_None identified._"


def build_report(state) -> Dict[str, Any]:
    info: ContractInfo = state["contract_info"]
    entities: EntityExtraction = state.get("entities", EntityExtraction())
    risks: List[RiskFinding] = state.get("risk_findings", [])
    mods: List[Modification] = state.get("modifications", [])
    compliance: List[ComplianceFinding] = state.get("compliance_findings", [])
    missing: List[MissingClause] = state.get("missing_clauses", [])
    conflicts: List[Conflict] = state.get("conflicts", [])
    pii: List[PIIFinding] = state.get("pii_findings", [])
    role_analyses: List[StepAnalysis] = state.get("role_analyses", [])

    report_json = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "contract_info": info.model_dump(),
        "primary_objective": state.get("primary_objective", ""),
        "specific_focus": state.get("specific_focus", ""),
        "overall_risk": {
            "score": state.get("overall_risk_score"),
            "level": state.get("overall_risk_level"),
        },
        "entities": entities.model_dump(),
        "risk_findings": [r.model_dump() for r in risks],
        "modifications": [m.model_dump() for m in mods],
        "compliance": [c.model_dump() for c in compliance],
        "missing_clauses": [m.model_dump() for m in missing],
        "conflicts": [c.model_dump() for c in conflicts],
        "pii": [p.model_dump() for p in pii],
        "role_analyses": [r.model_dump() for r in role_analyses],
    }

    md = []
    md.append("# Contract Review Report")
    md.append(f"**Generated:** {report_json['generated_at']}")
    md.append("\n## Executive Summary")
    md.append(f"- **Type:** {info.contract_type}")
    md.append(f"- **Industry:** {info.industry or 'N/A'}")
    md.append(f"- **Governing Law:** {info.governing_law or 'N/A'}")
    md.append(f"- **Effective Date:** {info.effective_date or 'N/A'}")
    md.append(f"- **Parties:** {', '.join(info.parties) if info.parties else 'N/A'}")
    md.append(
        f"- **Overall Risk:** **{state.get('overall_risk_level','?')}** "
        f"(score: {state.get('overall_risk_score','?')})"
    )
    md.append("")
    md.append(info.summary or "")

    md.append("\n## Risk Findings")
    md.append(_fmt_list(
        sorted(risks, key=lambda r: -RISK_WEIGHTS.get(r.risk_level, 0)),
        lambda r: f"- **[{r.risk_level} | {r.category}]** {r.title} — {r.description}  _Recommendation: {r.recommendation}_",
    ))

    md.append("\n## Suggested Modifications")
    md.append(_fmt_list(
        sorted(mods, key=lambda m: -RISK_WEIGHTS.get(m.risk_level, 0)),
        lambda m: f"- **[{m.risk_level}]** {m.original_text[:120]}… → {m.suggested_text[:120]}…  ({m.reason})",
    ))

    md.append("\n## Missing Clauses")
    md.append(_fmt_list(
        missing,
        lambda m: f"- **[{m.importance}]** {m.clause_title} — {m.why_missing_matters}",
    ))

    md.append("\n## Conflicts & Inconsistencies")
    md.append(_fmt_list(
        conflicts,
        lambda c: f"- **[{c.risk_level}]** {c.section_a} ↔ {c.section_b}: {c.description}  _Resolution: {c.resolution}_",
    ))

    md.append("\n## Compliance")
    md.append(_fmt_list(
        compliance,
        lambda c: f"- **{c.framework}** — {c.requirement}: **{c.status}**. {c.explanation}",
    ))

    md.append("\n## PII / Sensitive Data")
    md.append(_fmt_list(
        pii,
        lambda p: f"- **{p.type}**: '{p.excerpt[:80]}…' — {p.recommendation}",
    ))

    md.append("\n## Role-Based Analyses")
    for r in role_analyses:
        md.append(f"### {r.role}\n{r.analysis}")

    return {"final_report_md": "\n".join(md), "final_report_json": report_json}

"""LangGraph nodes for the contract analysis workflow.

Each node is small, single-responsibility, and returns a partial state update. All structured
LLM calls go through `safe_structured_call` so a transient failure doesn't blow up the whole run.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential

from prompts.prompts import PROMPTS

from .retrievers import ClauseRetriever
from .state import (
    ClauseCheckSummary,
    ComplianceFinding,
    Conflict,
    ContractInfo,
    EntityExtraction,
    MissingClause,
    Modification,
    PIIFinding,
    ReviewPlan,
    RiskFinding,
    StepAnalysis,
    aggregate_risk,
)
from .utils import split_into_sections

log = logging.getLogger("clauseai.nodes")


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10), reraise=True)
def _structured_call(model: ChatOpenAI, schema, system: str, human: str):
    return model.with_structured_output(schema).invoke([
        SystemMessage(content=system),
        HumanMessage(content=human),
    ])


def safe_structured_call(model: ChatOpenAI, schema, system: str, human: str, default):
    try:
        return _structured_call(model, schema, system, human)
    except Exception as e:
        log.warning("structured_call failed for %s: %s", schema.__name__, e)
        return default


# Wrapper schemas for list-returning nodes (with_structured_output expects a single model)
class _PIIList(BaseModel):
    items: List[PIIFinding] = Field(default_factory=list)


class _MissingList(BaseModel):
    items: List[MissingClause] = Field(default_factory=list)


class _ConflictList(BaseModel):
    items: List[Conflict] = Field(default_factory=list)


class _ComplianceList(BaseModel):
    items: List[ComplianceFinding] = Field(default_factory=list)


def make_nodes(
    llm: ChatOpenAI,
    llm_strong: ChatOpenAI,
    retriever: ClauseRetriever,
    *,
    compliance_frameworks: List[str],
    max_clause_checks: int = 12,
    progress_cb=None,
):
    """Build node callables bound to the provided models, retriever, and config."""

    def _emit(stage: str, message: str = "", **payload):
        if progress_cb:
            try:
                progress_cb({"stage": stage, "message": message, **payload})
            except Exception:
                pass

    # --- Nodes ---

    def classify(state):
        _emit("classify", "Classifying contract type and parties…")
        info = safe_structured_call(
            llm, ContractInfo, PROMPTS["classify"],
            f"Contract:\n{state['contract_text']}",
            ContractInfo(contract_type="Unknown", summary=""),
        )
        sections = split_into_sections(state["contract_text"])
        _emit("classify_done", f"{info.contract_type} • {len(sections)} sections")
        return {"contract_info": info, "sections_split": sections}

    def extract_entities(state):
        _emit("extract_entities", "Extracting parties, dates, financials, obligations…")
        ent = safe_structured_call(
            llm, EntityExtraction, PROMPTS["extract_entities"],
            f"Contract:\n{state['contract_text']}",
            EntityExtraction(),
        )
        _emit(
            "extract_entities_done",
            f"{len(ent.parties)} parties • {len(ent.financial_terms)} financial terms • "
            f"{len(ent.key_dates)} dates • {len(ent.obligations)} obligations",
        )
        return {"entities": ent}

    def detect_pii(state):
        _emit("detect_pii", "Scanning for PII / sensitive data…")
        out = safe_structured_call(
            llm, _PIIList, PROMPTS["detect_pii"],
            state["contract_text"], _PIIList(items=[]),
        )
        _emit("detect_pii_done", f"{len(out.items)} PII findings")
        return {"pii_findings": out.items}

    def retrieve_clauses(state):
        _emit("retrieve_clauses", "Retrieving reference clauses from library…")
        ct = state["contract_info"].contract_type
        expected = retriever.expected_clause_titles(ct)
        retrieved = retriever.reference_clauses(ct, k=max_clause_checks)
        _emit("retrieve_clauses_done", f"{len(retrieved)} reference clauses queued")
        return {"retrieved_clauses": retrieved, "expected_clauses": expected}

    def check_clause(state):
        clause = state.get("clause") or (
            state["retrieved_clauses"][0] if state.get("retrieved_clauses") else None
        )
        if not clause:
            return {"clause_check_results": []}
        title = clause.get("clause_title", "Clause")
        _emit("check_clause", f"Reviewing clause: {title}", clause_title=title)
        ref_block = (
            f"Reference clause:\nTitle: {title}\nText: {clause.get('clause_text','')}\n\n"
        )
        result = safe_structured_call(
            llm, StepAnalysis,
            PROMPTS["check_clause"] + "\n\n" + ref_block,
            state["contract_text"],
            StepAnalysis(role=title, analysis="(no analysis)"),
        )
        result.role = title
        return {
            "clause_check_results": [{"clause_title": title, "analysis": result.analysis}],
            "modifications": result.modifications,
            "risk_findings": result.risk_findings,
        }

    def missing_clauses(state):
        _emit("missing_clauses", "Detecting missing or weak clauses…")
        expected = state.get("expected_clauses", [])
        out = safe_structured_call(
            llm, _MissingList,
            PROMPTS["missing_clauses"].format(expected=json.dumps(expected)),
            state["contract_text"], _MissingList(items=[]),
        )
        _emit("missing_clauses_done", f"{len(out.items)} missing/weak clauses")
        return {"missing_clauses": out.items}

    def detect_conflicts(state):
        _emit("detect_conflicts", "Looking for internal conflicts between sections…")
        sections_blob = "\n\n".join(
            f"[Section {s['id']}] {s['title']}\n{s['text']}"
            for s in state.get("sections_split", [])
        )
        out = safe_structured_call(
            llm_strong, _ConflictList, PROMPTS["detect_conflicts"],
            sections_blob, _ConflictList(items=[]),
        )
        _emit("detect_conflicts_done", f"{len(out.items)} conflicts detected")
        return {"conflicts": out.items}

    def compliance(state):
        _emit("compliance", f"Compliance check: {', '.join(compliance_frameworks)}")
        out = safe_structured_call(
            llm_strong, _ComplianceList,
            PROMPTS["compliance"].format(frameworks=compliance_frameworks),
            state["contract_text"], _ComplianceList(items=[]),
        )
        _emit("compliance_done", f"{len(out.items)} compliance findings")
        return {"compliance_findings": out.items}

    def review_plan(state):
        _emit("review_plan", "Building role-based review plan…")
        info = state["contract_info"]
        plan = safe_structured_call(
            llm, ReviewPlan,
            PROMPTS["review_plan"].format(
                contract_type=info.contract_type,
                industry=info.industry or "general",
            ),
            (f"Primary objective: {state.get('primary_objective','')}\n"
             f"Specific focus: {state.get('specific_focus','')}"),
            ReviewPlan(roles=["Generalist Legal Counsel"]),
        )
        _emit("review_plan_done", f"{len(plan.roles)} roles selected", roles=plan.roles)
        return {"review_plan": plan}

    def role_review(state):
        role = state.get("role") or (
            state["review_plan"].roles[0] if state.get("review_plan") else "Counsel"
        )
        _emit("role_review", f"Reviewing as: {role}", role=role)
        result = safe_structured_call(
            llm, StepAnalysis,
            PROMPTS["role_review"].format(role=role),
            state["contract_text"],
            StepAnalysis(role=role, analysis=""),
        )
        result.role = role
        return {
            "role_analyses": [result],
            "modifications": result.modifications,
            "risk_findings": result.risk_findings,
        }

    def aggregate_risk_node(state):
        _emit("aggregate_risk", "Aggregating risk score…")
        score, level = aggregate_risk(state.get("risk_findings", []))
        _emit("aggregate_risk_done", f"Overall risk: {level} ({score})")
        return {"overall_risk_score": score, "overall_risk_level": level}

    return {
        "classify": classify,
        "extract_entities": extract_entities,
        "detect_pii": detect_pii,
        "retrieve_clauses": retrieve_clauses,
        "check_clause": check_clause,
        "missing_clauses": missing_clauses,
        "detect_conflicts": detect_conflicts,
        "compliance": compliance,
        "review_plan": review_plan,
        "role_review": role_review,
        "aggregate_risk": aggregate_risk_node,
    }

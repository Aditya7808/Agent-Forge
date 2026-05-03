"""Builds and runs the LangGraph contract analysis workflow."""
from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, List, Optional

from langchain_community.callbacks import get_openai_callback
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import Send
from langgraph.graph import END, START, StateGraph

from .nodes import make_nodes
from .reporter import build_report
from .retrievers import ClauseRetriever
from .state import ContractReviewState

log = logging.getLogger("clauseai.graph")


def build_graph(
    *,
    openai_model: str,
    openai_model_strong: str,
    embedding_model: str,
    temperature: float,
    clauses_path: str,
    compliance_frameworks: List[str],
    max_clause_checks: int,
    progress_cb: Optional[Callable[[Dict[str, Any]], None]] = None,
):
    """Compile the LangGraph workflow. Returns (graph, retriever)."""
    llm = ChatOpenAI(model=openai_model, temperature=temperature)
    llm_strong = ChatOpenAI(model=openai_model_strong, temperature=temperature)
    retriever = ClauseRetriever(clauses_path, embedding_model=embedding_model)

    nodes = make_nodes(
        llm, llm_strong, retriever,
        compliance_frameworks=compliance_frameworks,
        max_clause_checks=max_clause_checks,
        progress_cb=progress_cb,
    )

    builder = StateGraph(ContractReviewState)
    for name, fn in nodes.items():
        builder.add_node(name, fn)
    builder.add_node("final_report", lambda s: build_report(s))

    builder.add_edge(START, "classify")
    for nxt in [
        "extract_entities", "detect_pii", "retrieve_clauses",
        "missing_clauses", "detect_conflicts", "compliance", "review_plan",
    ]:
        builder.add_edge("classify", nxt)

    def fanout_clauses(state):
        return [
            Send("check_clause", {"contract_text": state["contract_text"], "clause": c})
            for c in (state.get("retrieved_clauses") or [])[:max_clause_checks]
        ]

    def fanout_roles(state):
        return [
            Send("role_review", {"contract_text": state["contract_text"], "role": role})
            for role in state["review_plan"].roles
        ]

    builder.add_conditional_edges("retrieve_clauses", fanout_clauses, ["check_clause"])
    builder.add_conditional_edges("review_plan", fanout_roles, ["role_review"])

    for src in [
        "extract_entities", "detect_pii", "check_clause", "missing_clauses",
        "detect_conflicts", "compliance", "role_review",
    ]:
        builder.add_edge(src, "aggregate_risk")

    builder.add_edge("aggregate_risk", "final_report")
    builder.add_edge("final_report", END)

    graph = builder.compile(checkpointer=MemorySaver())
    return graph, retriever


def run_analysis(
    *,
    contract_text: str,
    primary_objective: str,
    specific_focus: str,
    settings,
    progress_cb: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Dict[str, Any]:
    """Full end-to-end run. Returns the final state dict augmented with telemetry."""
    graph, _ = build_graph(
        openai_model=settings.openai_model,
        openai_model_strong=settings.openai_model_strong,
        embedding_model=settings.embedding_model,
        temperature=settings.temperature,
        clauses_path=settings.clauses_path,
        compliance_frameworks=settings.compliance_frameworks,
        max_clause_checks=settings.max_clause_checks,
        progress_cb=progress_cb,
    )

    config = {"configurable": {"thread_id": f"run-{int(time.time())}"}}
    input_state: ContractReviewState = {
        "contract_text": contract_text,
        "primary_objective": primary_objective,
        "specific_focus": specific_focus,
    }

    t0 = time.time()
    with get_openai_callback() as cb:
        result = graph.invoke(input_state, config=config)
    elapsed = time.time() - t0

    result["telemetry"] = {
        "elapsed_seconds": round(elapsed, 2),
        "prompt_tokens": cb.prompt_tokens,
        "completion_tokens": cb.completion_tokens,
        "total_tokens": cb.total_tokens,
        "total_cost_usd": round(cb.total_cost, 4),
    }
    return result

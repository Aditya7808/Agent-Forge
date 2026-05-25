import logging
from functools import lru_cache
from langgraph.graph import StateGraph, END
from backend.graph.state import AgentState
from backend.graph.nodes.classifier import classify_node, route_decision
from backend.graph.nodes.sql_node import sql_node
from backend.graph.nodes.rag_node import rag_node
from backend.graph.nodes.trust_node import trust_node

logger = logging.getLogger(__name__)


def build_workflow():
    graph = StateGraph(AgentState)

    graph.add_node("classify", classify_node)
    graph.add_node("sql", sql_node)
    graph.add_node("rag", rag_node)
    graph.add_node("trust", trust_node)

    graph.set_entry_point("classify")

    graph.add_conditional_edges(
        "classify",
        route_decision,
        {
            "sql": "sql",
            "rag": "rag",
        }
    )

    graph.add_edge("sql", END)
    graph.add_edge("rag", "trust")
    graph.add_edge("trust", END)

    compiled = graph.compile()
    logger.info("LangGraph workflow compiled successfully")
    return compiled


@lru_cache(maxsize=1)
def get_workflow():
    return build_workflow()

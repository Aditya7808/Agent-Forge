import logging
from backend.graph.state import AgentState
from backend.services.rag_chain import run_rag_chain

logger = logging.getLogger(__name__)


def rag_node(state: AgentState) -> AgentState:
    query = state["query"]
    session_id = state.get("session_id", "default")
    logger.info(f"RAG node processing: {query[:60]}")

    try:
        result = run_rag_chain(session_id, query)
        return {
            **state,
            "response": result["response"],
            "context": result.get("context", ""),
            "sources": result.get("sources", []),
            "metadata": {
                "sources": result.get("sources", []),
                "no_documents": result.get("no_documents", False),
            },
            "error": result.get("error"),
        }
    except Exception as e:
        logger.exception("RAG node failed")
        return {
            **state,
            "response": f"I encountered an error retrieving documents: {str(e)}",
            "error": str(e),
        }

import logging
from backend.graph.state import AgentState
from backend.services.trust_scorer import validate_response

logger = logging.getLogger(__name__)


def trust_node(state: AgentState) -> AgentState:
    if state.get("metadata", {}).get("no_documents"):
        return state

    if not state.get("context"):
        return state

    query = state["query"]
    session_id = state.get("session_id", "default")
    response = state.get("response", "")
    context = state.get("context", "")

    logger.info(f"Trust scoring for: {query[:60]}")

    try:
        result = validate_response(
            query=query,
            context=context,
            response=response,
            session_id=session_id,
        )
        return {
            **state,
            "response": result["validated_response"],
            "trust_score": result.get("trust_score"),
            "guardrailed": result.get("guardrailed", False),
            "metadata": {
                **state.get("metadata", {}),
                "guardrailed": result.get("guardrailed", False),
            },
        }
    except Exception as e:
        logger.warning(f"Trust scoring failed (non-fatal): {e}")
        return state

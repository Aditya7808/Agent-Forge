import logging
from backend.graph.state import AgentState
from backend.services.sql_chain import run_sql_chain

logger = logging.getLogger(__name__)


def sql_node(state: AgentState) -> AgentState:
    query = state["query"]
    logger.info(f"SQL node processing: {query[:60]}")

    try:
        result = run_sql_chain(query)
        return {
            **state,
            "response": result["response"],
            "sql_query": result.get("sql_query"),
            "sql_data": result.get("data", []),
            "metadata": {"data": result.get("data", [])},
            "error": result.get("error"),
        }
    except Exception as e:
        logger.exception("SQL node failed")
        return {
            **state,
            "response": f"I encountered an error querying the database: {str(e)}",
            "error": str(e),
        }

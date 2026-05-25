import logging
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from backend.graph.state import AgentState
from backend.services.llm import get_classifier_llm
from backend.services.vector_store import has_documents

logger = logging.getLogger(__name__)

CLASSIFIER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an intelligent query router. Classify the user's query into exactly one of two categories:

1. "sql" - Queries about US city statistics, population data, or state information.
   Examples: "What is the population of Houston?", "Which cities are in California?", "Top 5 largest cities"

2. "rag" - Queries about documents, reports, files, or any non-city topic.
   Examples: "Summarize the report", "What does the document say about X?", "Key findings"

{document_note}

Respond with ONLY the single word "sql" or "rag". Nothing else."""),
    ("user", "{query}")
])


def classify_node(state: AgentState) -> AgentState:
    query = state["query"]
    session_id = state.get("session_id", "default")

    document_note = (
        "NOTE: Documents have been uploaded for this session."
        if has_documents(session_id)
        else "NOTE: No documents are currently uploaded. Default to 'sql' for city/population queries; only use 'rag' if the user is clearly asking about non-city content."
    )

    llm = get_classifier_llm()
    chain = CLASSIFIER_PROMPT | llm | StrOutputParser()

    try:
        classification = chain.invoke({
            "query": query,
            "document_note": document_note,
        }).strip().lower()
    except Exception as e:
        logger.exception("Classification failed")
        return {**state, "route": "sql", "error": f"Classification fallback: {e}"}

    route = "sql" if "sql" in classification else "rag"
    logger.info(f"Classified query as '{route}': {query[:60]}")
    return {**state, "route": route}


def route_decision(state: AgentState) -> str:
    return state.get("route", "sql")

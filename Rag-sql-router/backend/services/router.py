from openai import OpenAI
from backend.config import settings
from backend.models import RouteType

ROUTER_SYSTEM_PROMPT = """You are an intelligent query router. Your job is to classify user queries into one of two categories:

1. "sql" - Use this when the query is about US city statistics, population data, or state information.
   Examples: "What is the population of Houston?", "Which cities are in California?", "What's the largest city?"

2. "rag" - Use this when the query is about anything else, especially when it requires searching through uploaded documents.
   Examples: "What does the report say about Q4 revenue?", "Summarize the key findings", "What is the weather policy?"

Respond with ONLY the word "sql" or "rag". Nothing else."""


def classify_query(query: str, has_documents: bool = False) -> RouteType:
    client = OpenAI(api_key=settings.openai_api_key)

    context_note = ""
    if not has_documents:
        context_note = "\nNote: No documents have been uploaded yet. If the query is NOT about US city data, still route to 'rag' but it may return no results."

    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": ROUTER_SYSTEM_PROMPT + context_note},
            {"role": "user", "content": query}
        ],
        temperature=0,
        max_tokens=10,
    )

    classification = response.choices[0].message.content.strip().lower()

    if "sql" in classification:
        return RouteType.SQL
    return RouteType.RAG

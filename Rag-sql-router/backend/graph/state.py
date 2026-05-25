from typing import TypedDict, Optional, List, Literal, Any


class AgentState(TypedDict, total=False):
    query: str
    session_id: str
    route: Literal["sql", "rag"]
    response: str
    sql_query: Optional[str]
    sql_data: Optional[List[dict]]
    context: Optional[str]
    sources: Optional[List[str]]
    trust_score: Optional[float]
    guardrailed: bool
    error: Optional[str]
    metadata: dict

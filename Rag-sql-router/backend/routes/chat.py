import logging
from fastapi import APIRouter, HTTPException
from backend.models import ChatRequest, ChatResponse, RouteType
from backend.graph import get_workflow

router = APIRouter(prefix="/api/chat", tags=["chat"])
logger = logging.getLogger(__name__)


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    session_id = request.session_id or "default"

    try:
        workflow = get_workflow()
        final_state = await workflow.ainvoke({
            "query": request.message,
            "session_id": session_id,
            "metadata": {},
        })
    except Exception as e:
        logger.exception("Workflow invocation failed")
        raise HTTPException(status_code=500, detail=f"Workflow failed: {str(e)}")

    if final_state.get("error") and not final_state.get("response"):
        raise HTTPException(status_code=500, detail=final_state["error"])

    route = final_state.get("route", "sql")

    return ChatResponse(
        response=final_state.get("response", ""),
        route_used=RouteType.SQL if route == "sql" else RouteType.RAG,
        trust_score=final_state.get("trust_score"),
        sql_query=final_state.get("sql_query"),
        metadata=final_state.get("metadata", {}),
    )

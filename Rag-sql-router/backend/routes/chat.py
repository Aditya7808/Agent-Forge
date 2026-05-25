from fastapi import APIRouter, HTTPException
from backend.models import ChatRequest, ChatResponse, RouteType
from backend.services.router import classify_query
from backend.services.sql_engine import natural_language_to_sql_response
from backend.services.rag_engine import query_documents, sessions
from backend.services.trust_scorer import validate_response

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    session_id = request.session_id or "default"
    has_documents = session_id in sessions

    try:
        route = classify_query(request.message, has_documents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Routing failed: {str(e)}")

    if route == RouteType.SQL:
        try:
            result = natural_language_to_sql_response(request.message)
            return ChatResponse(
                response=result["response"],
                route_used=RouteType.SQL,
                sql_query=result.get("sql_query"),
                metadata={"data": result.get("data", [])}
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"SQL processing failed: {str(e)}")

    else:
        try:
            rag_result = query_documents(session_id, request.message)

            trust_data = validate_response(
                query=request.message,
                context=rag_result.get("context", ""),
                response=rag_result["response"],
                session_id=session_id,
            )

            return ChatResponse(
                response=trust_data["validated_response"],
                route_used=RouteType.RAG,
                trust_score=trust_data["trust_score"],
                metadata={
                    "sources": rag_result.get("sources", []),
                    "guardrailed": trust_data.get("guardrailed", False),
                }
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"RAG processing failed: {str(e)}")

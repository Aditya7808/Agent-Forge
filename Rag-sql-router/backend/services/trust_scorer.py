import os
import uuid
import logging
from backend.config import settings

logger = logging.getLogger(__name__)

_codex_project = None
_codex_session_id = None


def initialize_codex(session_id: str):
    global _codex_project, _codex_session_id

    if not settings.codex_api_key or settings.codex_api_key.startswith("your-"):
        return None

    os.environ["CODEX_API_KEY"] = settings.codex_api_key

    try:
        from cleanlab_codex.client import Client
        from cleanlab_codex.project import Project

        if _codex_project and _codex_session_id == session_id:
            return _codex_project

        client = Client()
        project_id = str(uuid.uuid4())[:8]
        project = client.create_project(name=f"RAG-SQL-Router-{project_id}")
        access_key = project.create_access_key("default key")
        _codex_project = Project.from_access_key(access_key)
        _codex_session_id = session_id
        return _codex_project
    except Exception as e:
        logger.warning(f"Codex initialization failed: {e}")
        return None


def validate_response(
    query: str,
    context: str,
    response: str,
    session_id: str
) -> dict:
    project = initialize_codex(session_id)

    if not project:
        return {
            "trust_score": None,
            "validated_response": response,
            "guardrailed": False,
        }

    try:
        prompt = (
            "You are a meticulous document analyst. Answer based exclusively on context.\n"
            f"Context: {context}\n"
            f"Question: {query}\n"
            "Answer:"
        )
        messages = [{"role": "user", "content": prompt}]

        result = project.validate(
            messages=messages,
            query=query,
            context=context,
            response=response,
        )

        trust_score = result.model_dump()["eval_scores"]["trustworthiness"]["score"]

        if result.expert_answer and result.escalated_to_sme:
            final_response = result.expert_answer
        elif result.should_guardrail:
            final_response = "I couldn't find a reliable answer in the documents. Could you rephrase your question or provide more context?"
        else:
            final_response = response

        return {
            "trust_score": float(trust_score),
            "validated_response": final_response,
            "guardrailed": bool(getattr(result, "should_guardrail", False)),
        }
    except Exception as e:
        logger.warning(f"Codex validation error: {e}")
        return {
            "trust_score": None,
            "validated_response": response,
            "guardrailed": False,
        }

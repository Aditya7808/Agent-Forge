import logging
from typing import List
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableParallel, RunnableLambda, RunnablePassthrough
from backend.config import settings
from backend.services.llm import get_llm
from backend.services.vector_store import get_vector_store, has_documents

logger = logging.getLogger(__name__)

RAG_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a meticulous document analyst. Answer the user's question based EXCLUSIVELY on the provided context.

Rules:
1. Ground your entire response in the facts from the context. Do not use prior knowledge.
2. If multiple parts are relevant, synthesize them into a coherent answer.
3. If the context lacks sufficient information, state: "The provided documents do not contain enough information to answer this question."
4. Be specific and cite information directly from the context where possible."""),
    ("user", "Context:\n{context}\n\n---\n\nQuestion: {question}")
])


def _format_docs(docs: List[Document]) -> str:
    if not docs:
        return ""
    formatted = []
    for i, doc in enumerate(docs, 1):
        source = doc.metadata.get("source", "unknown")
        formatted.append(f"[Source {i}: {source}]\n{doc.page_content}")
    return "\n\n---\n\n".join(formatted)


def _extract_sources(docs: List[Document]) -> List[str]:
    return list({d.metadata.get("source", "unknown") for d in docs})


def run_rag_chain(session_id: str, question: str) -> dict:
    if not has_documents(session_id):
        return {
            "response": "No documents have been uploaded yet. Please upload documents to use the RAG pipeline, or ask a question about US city statistics.",
            "sources": [],
            "context": "",
            "no_documents": True,
        }

    vs = get_vector_store(session_id)
    retriever = vs.as_retriever(search_kwargs={"k": settings.similarity_top_k})

    try:
        retrieved_docs = retriever.invoke(question)
    except Exception as e:
        logger.exception("Retrieval failed")
        return {
            "response": f"Failed to retrieve documents: {str(e)}",
            "sources": [],
            "context": "",
            "error": str(e),
        }

    if not retrieved_docs:
        return {
            "response": "No relevant information found in the uploaded documents for your query.",
            "sources": [],
            "context": "",
        }

    context_str = _format_docs(retrieved_docs)
    sources = _extract_sources(retrieved_docs)

    llm = get_llm()
    chain = RAG_PROMPT | llm | StrOutputParser()

    try:
        answer = chain.invoke({"context": context_str, "question": question})
    except Exception as e:
        logger.exception("Generation failed")
        return {
            "response": f"Failed to generate answer: {str(e)}",
            "sources": sources,
            "context": context_str,
            "error": str(e),
        }

    return {
        "response": answer,
        "sources": sources,
        "context": context_str,
    }

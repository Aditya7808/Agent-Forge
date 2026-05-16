"""Retrieval-Augmented Generation orchestrator.

Combines an embedder, a vector store, and an LLM into a query-time pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator, List, Optional

from audio_chat.config import Settings
from audio_chat.embeddings import BaseEmbedder
from audio_chat.llm import ChatMessage, OpenAIChatLLM
from audio_chat.logger import get_logger
from audio_chat.vector_store import QdrantStore

logger = get_logger("rag")


SYSTEM_PROMPT = (
    "You are a helpful assistant for an audio-RAG application. The user has uploaded "
    "an audio file (meeting, podcast, lecture, voice note, etc.) which has been "
    "transcribed and indexed. For each turn you receive the most relevant transcript "
    "excerpts and the user's message.\n\n"
    "Guidelines:\n"
    "• Ground every factual claim in the provided context — never invent details that "
    "are not in the transcript.\n"
    "• You ARE allowed (and expected) to SUMMARIZE, EXPLAIN, TRANSLATE, REPHRASE, or "
    "ANSWER FOLLOW-UP QUESTIONS about the context. \"Explain this in Hindi\", "
    "\"summarize\", \"what is this about?\", \"give me bullet points\" are all valid "
    "and should be answered using the context — do NOT refuse them.\n"
    "• If the user asks for something that the transcript truly does not contain "
    "(e.g. a person/topic that never appears), reply: \"I don't know based on the "
    "provided audio.\"\n"
    "• If the transcript is very short, just work with what's there — a one-line "
    "transcript can still be summarized or translated.\n"
    "• For greetings or chit-chat (\"hi\", \"hello\"), respond briefly and invite the "
    "user to ask something about the audio — don't refuse.\n"
    "• When quoting, attribute to the speaker label when available "
    "(e.g. \"Speaker A said ...\").\n"
    "• Be concise unless the user asks for detail."
)


QA_TEMPLATE = (
    "Transcript excerpts retrieved for this turn (most relevant first):\n"
    "=====================\n"
    "{context}\n"
    "=====================\n"
    "Recent conversation:\n{history}\n"
    "=====================\n"
    "User message: {query}\n\n"
    "Respond following the guidelines. If the user asked you to summarize, explain, "
    "or translate, do so based on the transcript above — do not refuse."
)


@dataclass
class RetrievedChunk:
    text: str
    score: float
    metadata: dict = field(default_factory=dict)


class RAGEngine:
    def __init__(
        self,
        embedder: BaseEmbedder,
        store: QdrantStore,
        llm: OpenAIChatLLM,
        settings: Settings,
        system_prompt: Optional[str] = None,
    ):
        self.embedder = embedder
        self.store = store
        self.llm = llm
        self.settings = settings
        # Store explicit override; fall back to module-level SYSTEM_PROMPT at use
        # time so hot-reloads of the prompt take effect without re-instantiating.
        self._system_prompt_override = system_prompt

    @property
    def system_prompt(self) -> str:
        return self._system_prompt_override or SYSTEM_PROMPT

    # ---- retrieval ----

    def retrieve(self, query: str, top_k: Optional[int] = None) -> List[RetrievedChunk]:
        k = top_k or self.settings.retrieval_top_k
        query_vec = self.embedder.embed_query(query)
        raw = self.store.search(query_vec, top_k=k)
        chunks: List[RetrievedChunk] = []
        for r in raw:
            payload = r["payload"] or {}
            text = payload.get("text") or payload.get("context") or ""
            if not text:
                continue
            chunks.append(
                RetrievedChunk(
                    text=text,
                    score=r["score"],
                    metadata={k_: v for k_, v in payload.items() if k_ != "text"},
                )
            )
        logger.info("Retrieved %d chunks for query (top_k=%d)", len(chunks), k)
        return chunks

    # ---- prompt building ----

    def _build_context(self, chunks: List[RetrievedChunk]) -> str:
        if not chunks:
            return "(no relevant context found)"
        pieces: List[str] = []
        total = 0
        for c in chunks:
            block = c.text.strip()
            if total + len(block) + 6 > self.settings.max_context_chars:
                break
            pieces.append(block)
            total += len(block) + 6
        return "\n\n---\n\n".join(pieces)

    def _build_messages(
        self,
        query: str,
        chunks: List[RetrievedChunk],
        history: Optional[List[ChatMessage]] = None,
    ) -> List[ChatMessage]:
        history = history or []
        history_text = "\n".join(f"{m.role}: {m.content}" for m in history[-6:]) or "(none)"
        user_prompt = QA_TEMPLATE.format(
            context=self._build_context(chunks),
            history=history_text,
            query=query,
        )
        return [
            ChatMessage(role="system", content=self.system_prompt),
            ChatMessage(role="user", content=user_prompt),
        ]

    # ---- query APIs ----

    def stream_query(
        self,
        query: str,
        history: Optional[List[ChatMessage]] = None,
        top_k: Optional[int] = None,
    ) -> Iterator[str]:
        chunks = self.retrieve(query, top_k=top_k)
        messages = self._build_messages(query, chunks, history)
        yield from self.llm.stream(messages)

    def query(
        self,
        query: str,
        history: Optional[List[ChatMessage]] = None,
        top_k: Optional[int] = None,
    ) -> str:
        chunks = self.retrieve(query, top_k=top_k)
        messages = self._build_messages(query, chunks, history)
        return self.llm.complete(messages)

    def query_with_sources(
        self,
        query: str,
        history: Optional[List[ChatMessage]] = None,
        top_k: Optional[int] = None,
    ) -> dict:
        """Returns {answer, sources} for callers that want citations."""
        chunks = self.retrieve(query, top_k=top_k)
        messages = self._build_messages(query, chunks, history)
        answer = self.llm.complete(messages)
        return {
            "answer": answer,
            "sources": [
                {"text": c.text, "score": c.score, "metadata": c.metadata}
                for c in chunks
            ],
        }

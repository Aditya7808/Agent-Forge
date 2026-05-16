"""High-level facade: one object that owns the full audio → answer flow.

Intended as the primary integration point for other applications:

    from audio_chat import AudioChatPipeline
    pipe = AudioChatPipeline.from_env()
    pipe.ingest_audio("meeting.mp3")
    for token in pipe.stream_query("What did Alice decide?"):
        print(token, end="")
"""

from __future__ import annotations

from typing import Iterator, List, Optional, Sequence

from audio_chat.chunking import chunk_segments, segments_to_text
from audio_chat.config import Settings
from audio_chat.embeddings import BaseEmbedder, build_embedder
from audio_chat.llm import ChatMessage, OpenAIChatLLM, build_llm
from audio_chat.logger import configure_logging, get_logger
from audio_chat.rag import RAGEngine
from audio_chat.transcriber import BaseTranscriber, TranscriptSegment, build_transcriber
from audio_chat.vector_store import QdrantStore

logger = get_logger("pipeline")


class AudioChatPipeline:
    """Facade tying together transcription, embedding, vector store, and RAG."""

    def __init__(
        self,
        settings: Settings,
        *,
        transcriber: Optional[BaseTranscriber] = None,
        embedder: Optional[BaseEmbedder] = None,
        store: Optional[QdrantStore] = None,
        llm: Optional[OpenAIChatLLM] = None,
    ):
        settings.validate()
        configure_logging(level=settings.log_level, json_format=settings.log_json)
        self.settings = settings
        self.transcriber = transcriber or build_transcriber(settings)
        self.embedder = embedder or build_embedder(settings)
        # vector dim must match the active embedder
        vector_dim = self.embedder.dim
        self.store = store or QdrantStore(settings, vector_dim=vector_dim)
        self.store.ensure_collection()
        self.llm = llm or build_llm(settings)
        self.rag = RAGEngine(self.embedder, self.store, self.llm, settings)
        self._history: List[ChatMessage] = []

    # ---- constructors ----

    @classmethod
    def from_env(cls) -> "AudioChatPipeline":
        return cls(Settings.from_env())

    @classmethod
    def from_kwargs(cls, **kwargs) -> "AudioChatPipeline":
        base = Settings.from_env()
        for k, v in kwargs.items():
            if hasattr(base, k):
                setattr(base, k, v)
            else:
                raise TypeError(f"Unknown setting: {k!r}")
        return cls(base)

    # ---- ingestion ----

    def ingest_audio(self, audio_path: str) -> dict:
        """Transcribe an audio file and index its chunks. Returns a summary dict."""
        logger.info("Ingesting audio: %s", audio_path)
        segments = self.transcriber.transcribe(audio_path)
        return self.ingest_segments(segments)

    def ingest_segments(self, segments: Sequence[TranscriptSegment]) -> dict:
        """Index already-transcribed segments (skip transcription)."""
        chunks = chunk_segments(
            segments,
            chunk_size=self.settings.chunk_size,
            chunk_overlap=self.settings.chunk_overlap,
        )
        if not chunks:
            logger.warning("No chunks produced from segments — nothing to index.")
            return {"segments": len(segments), "chunks": 0, "indexed": 0}

        embeddings = self.embedder.embed_documents(chunks)
        payloads = [{"text": ch, "source": "audio"} for ch in chunks]
        n = self.store.upsert(embeddings, payloads)
        return {
            "segments": len(segments),
            "chunks": len(chunks),
            "indexed": n,
            "transcript_preview": segments_to_text(segments)[:500],
        }

    def ingest_text(self, text: str, *, source: str = "text") -> dict:
        """Index a raw text document (e.g. a transcript pasted by the user)."""
        if not text.strip():
            return {"chunks": 0, "indexed": 0}
        seg = TranscriptSegment(speaker=None, text=text.strip())
        chunks = chunk_segments(
            [seg],
            chunk_size=self.settings.chunk_size,
            chunk_overlap=self.settings.chunk_overlap,
        )
        embeddings = self.embedder.embed_documents(chunks)
        payloads = [{"text": ch, "source": source} for ch in chunks]
        n = self.store.upsert(embeddings, payloads)
        return {"chunks": len(chunks), "indexed": n}

    # ---- querying ----

    def stream_query(self, query: str, top_k: Optional[int] = None) -> Iterator[str]:
        chunks: List[str] = []
        for tok in self.rag.stream_query(query, history=self._history, top_k=top_k):
            chunks.append(tok)
            yield tok
        full = "".join(chunks).strip()
        if full:
            self._history.append(ChatMessage(role="user", content=query))
            self._history.append(ChatMessage(role="assistant", content=full))

    def query(self, query: str, top_k: Optional[int] = None) -> str:
        answer = self.rag.query(query, history=self._history, top_k=top_k)
        self._history.append(ChatMessage(role="user", content=query))
        self._history.append(ChatMessage(role="assistant", content=answer))
        return answer

    def query_with_sources(self, query: str, top_k: Optional[int] = None) -> dict:
        result = self.rag.query_with_sources(query, history=self._history, top_k=top_k)
        self._history.append(ChatMessage(role="user", content=query))
        self._history.append(ChatMessage(role="assistant", content=result["answer"]))
        return result

    # ---- state management ----

    def reset_history(self) -> None:
        self._history.clear()

    def reset_index(self) -> None:
        """Drop the vector collection and recreate it (clears all ingested data)."""
        self.store.delete_collection()
        self.store.ensure_collection()
        self.reset_history()

    def stats(self) -> dict:
        return {
            "collection": self.store.collection,
            "points": self.store.count(),
            "history_messages": len(self._history),
            "llm_model": self.llm.model,
            "embedding_model": getattr(self.embedder, "model", None)
            or getattr(self.embedder, "model_name", None),
            "embedding_dim": self.embedder.dim,
            "transcription_provider": self.settings.transcription_provider,
        }

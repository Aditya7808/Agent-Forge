"""Backwards-compatibility shim for the original `code_rag` module.

The implementation moved into the `audio_chat` package. This file preserves
the old import paths so existing notebooks and scripts keep working.

New code should import from `audio_chat` directly:

    from audio_chat import AudioChatPipeline
"""

from __future__ import annotations

import warnings
from typing import Dict, List, Optional

from audio_chat import AudioChatPipeline, Settings, get_settings
from audio_chat.chunking import chunk_segments
from audio_chat.embeddings import HuggingFaceEmbedder, OpenAIEmbedder, build_embedder
from audio_chat.llm import OpenAIChatLLM, build_llm
from audio_chat.rag import RAGEngine
from audio_chat.transcriber import (
    AssemblyAITranscriber,
    OpenAITranscriber,
    TranscriptSegment,
    build_transcriber,
)
from audio_chat.vector_store import QdrantStore

warnings.warn(
    "`code_rag` is a compatibility shim. Import from `audio_chat` instead "
    "(e.g. `from audio_chat import AudioChatPipeline`).",
    DeprecationWarning,
    stacklevel=2,
)


def batch_iterate(lst, batch_size):
    """Legacy helper: yield successive batches from `lst`."""
    for i in range(0, len(lst), batch_size):
        yield lst[i : i + batch_size]


class EmbedData:
    """Legacy wrapper that builds an embedder from kwargs/env and caches embeddings."""

    def __init__(self, embed_model_name: Optional[str] = None, batch_size: int = 32):
        settings = Settings.from_env()
        if embed_model_name:
            # The old default was a HF model; honor that if a HF-style name was passed.
            settings.embedding_provider = "huggingface"
            settings.hf_embedding_model = embed_model_name
        settings.embedding_batch_size = batch_size
        self.embed_model = build_embedder(settings)
        self.contexts: List[str] = []
        self.embeddings: List[List[float]] = []

    def embed(self, contexts: List[str]) -> None:
        self.contexts = list(contexts)
        self.embeddings = self.embed_model.embed_documents(self.contexts)


class QdrantVDB_QB:
    """Legacy thin wrapper kept for old code paths."""

    def __init__(self, collection_name: str, vector_dim: int = 1536, batch_size: int = 512):
        settings = Settings.from_env()
        settings.qdrant_collection = collection_name
        settings.qdrant_upsert_batch_size = batch_size
        self._settings = settings
        self.collection_name = collection_name
        self.vector_dim = vector_dim
        self.store: Optional[QdrantStore] = None

    def define_client(self) -> None:
        self.store = QdrantStore(self._settings, vector_dim=self.vector_dim)
        # mirror old attribute name
        self.client = self.store.client

    def create_collection(self) -> None:
        assert self.store is not None, "Call define_client() first."
        self.store.ensure_collection()

    def ingest_data(self, embeddata: "EmbedData") -> None:
        assert self.store is not None, "Call define_client() first."
        payloads = [{"text": c, "context": c} for c in embeddata.contexts]
        self.store.upsert(embeddata.embeddings, payloads)


class Retriever:
    """Legacy retriever facade — delegates to the new QdrantStore."""

    def __init__(self, vector_db: "QdrantVDB_QB", embeddata: "EmbedData"):
        self.vector_db = vector_db
        self.embeddata = embeddata

    def search(self, query: str, top_k: int = 5):
        assert self.vector_db.store is not None, "Call define_client()/create_collection() first."
        vec = self.embeddata.embed_model.embed_query(query)
        return self.vector_db.store.search(vec, top_k=top_k)


class RAG:
    """Legacy RAG facade using the new RAGEngine internally."""

    def __init__(self, retriever: "Retriever", llm_name: Optional[str] = None):
        settings = Settings.from_env()
        if llm_name:
            settings.llm_model = llm_name
        self._settings = settings
        self._llm = build_llm(settings)
        self._engine = RAGEngine(
            embedder=retriever.embeddata.embed_model,
            store=retriever.vector_db.store,  # type: ignore[arg-type]
            llm=self._llm,
            settings=settings,
        )

    def query(self, query: str):
        """Returns a generator of token strings (matches the old streaming API)."""
        return self._engine.stream_query(query)


class Transcribe:
    """Legacy AssemblyAI transcriber kept for parity with the old API."""

    def __init__(self, api_key: str):
        settings = Settings.from_env()
        settings.transcription_provider = "assemblyai"
        settings.assemblyai_api_key = api_key
        self._impl = AssemblyAITranscriber(settings)

    def transcribe_audio(self, audio_path: str) -> List[Dict[str, str]]:
        segs = self._impl.transcribe(audio_path)
        return [{"speaker": s.speaker or "Speaker", "text": s.text} for s in segs]


__all__ = [
    # Legacy
    "batch_iterate",
    "EmbedData",
    "QdrantVDB_QB",
    "Retriever",
    "RAG",
    "Transcribe",
    # New API re-exports
    "AudioChatPipeline",
    "Settings",
    "get_settings",
    "OpenAIEmbedder",
    "HuggingFaceEmbedder",
    "OpenAITranscriber",
    "AssemblyAITranscriber",
    "TranscriptSegment",
    "QdrantStore",
    "RAGEngine",
    "OpenAIChatLLM",
    "build_embedder",
    "build_transcriber",
    "build_llm",
    "chunk_segments",
]

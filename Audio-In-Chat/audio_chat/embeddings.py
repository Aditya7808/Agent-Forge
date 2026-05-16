"""Embedding providers for audio_chat.

OpenAI is the default. HuggingFace remains available for fully-local deployments.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Sequence

from audio_chat.config import Settings
from audio_chat.exceptions import EmbeddingError
from audio_chat.logger import get_logger

logger = get_logger("embeddings")


def _batch(seq: Sequence, size: int):
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


class BaseEmbedder(ABC):
    """Embedder interface — embed many documents or a single query."""

    dim: int

    @abstractmethod
    def embed_documents(self, texts: Sequence[str]) -> List[List[float]]:
        ...

    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        ...


class OpenAIEmbedder(BaseEmbedder):
    """Embeddings via OpenAI's `text-embedding-3-*` family."""

    def __init__(self, settings: Settings):
        try:
            from openai import OpenAI
        except ImportError as e:
            raise EmbeddingError(
                "openai package is required for OpenAIEmbedder. "
                "Install with: pip install openai"
            ) from e

        if not settings.openai_api_key:
            raise EmbeddingError("OPENAI_API_KEY is required for OpenAIEmbedder.")

        self._client = OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
        self.model = settings.embedding_model
        self.dim = settings.embedding_dim
        self.batch_size = settings.embedding_batch_size
        logger.info(
            "OpenAIEmbedder initialized | model=%s dim=%d batch=%d",
            self.model, self.dim, self.batch_size,
        )

    def embed_documents(self, texts: Sequence[str]) -> List[List[float]]:
        if not texts:
            return []
        vectors: List[List[float]] = []
        for chunk in _batch(list(texts), self.batch_size):
            try:
                resp = self._client.embeddings.create(model=self.model, input=chunk)
            except Exception as e:
                raise EmbeddingError(f"OpenAI embeddings failed: {e}") from e
            vectors.extend([d.embedding for d in resp.data])
        return vectors

    def embed_query(self, text: str) -> List[float]:
        try:
            resp = self._client.embeddings.create(model=self.model, input=[text])
        except Exception as e:
            raise EmbeddingError(f"OpenAI embeddings failed: {e}") from e
        return resp.data[0].embedding


class HuggingFaceEmbedder(BaseEmbedder):
    """Local embeddings via sentence-transformers / HuggingFace.

    Heavier dependency (torch + transformers) — only loaded on demand.
    """

    def __init__(self, settings: Settings):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            raise EmbeddingError(
                "sentence-transformers is required for HuggingFaceEmbedder. "
                "Install with: pip install sentence-transformers"
            ) from e

        self.model_name = settings.hf_embedding_model
        self.batch_size = settings.embedding_batch_size
        logger.info("Loading HF embedding model %s ...", self.model_name)
        self._model = SentenceTransformer(
            self.model_name,
            cache_folder=settings.hf_cache_dir,
        )
        self.dim = self._model.get_sentence_embedding_dimension()
        logger.info("HuggingFaceEmbedder ready | dim=%d", self.dim)

    def embed_documents(self, texts: Sequence[str]) -> List[List[float]]:
        if not texts:
            return []
        try:
            arr = self._model.encode(
                list(texts),
                batch_size=self.batch_size,
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True,
            )
        except Exception as e:
            raise EmbeddingError(f"HuggingFace embedding failed: {e}") from e
        return arr.tolist()

    def embed_query(self, text: str) -> List[float]:
        arr = self._model.encode(
            [text],
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return arr[0].tolist()


def build_embedder(settings: Settings) -> BaseEmbedder:
    """Factory: pick an embedder implementation from settings."""
    provider = settings.embedding_provider
    if provider == "openai":
        return OpenAIEmbedder(settings)
    if provider == "huggingface":
        return HuggingFaceEmbedder(settings)
    raise EmbeddingError(f"Unknown embedding provider: {provider!r}")

"""Qdrant vector-store wrapper.

Supports three deployment modes via the QDRANT_URL setting:
  * ":memory:"            — ephemeral in-process Qdrant (zero-config demos / tests)
  * "http://host:6333"    — self-hosted Qdrant
  * "https://...qdrant.io" + QDRANT_API_KEY — Qdrant Cloud
"""

from __future__ import annotations

import uuid
from typing import Iterable, List, Sequence

from audio_chat.config import Settings
from audio_chat.exceptions import VectorStoreError
from audio_chat.logger import get_logger

logger = get_logger("vector_store")


class QdrantStore:
    """Thin, typed wrapper around the Qdrant Python client."""

    def __init__(self, settings: Settings, vector_dim: int):
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.http import models as qmodels
        except ImportError as e:
            raise VectorStoreError(
                "qdrant-client is required. Install with: pip install qdrant-client"
            ) from e

        self._qmodels = qmodels
        self.collection = settings.qdrant_collection
        self.vector_dim = vector_dim
        self.batch_size = settings.qdrant_upsert_batch_size

        client_kwargs = {"prefer_grpc": settings.qdrant_prefer_grpc}
        if settings.qdrant_url == ":memory:":
            client_kwargs["location"] = ":memory:"
            logger.warning(
                "Qdrant running in :memory: mode — data is lost on restart. "
                "Set QDRANT_URL for persistence."
            )
        else:
            client_kwargs["url"] = settings.qdrant_url
            if settings.qdrant_api_key:
                client_kwargs["api_key"] = settings.qdrant_api_key

        try:
            self.client = QdrantClient(**client_kwargs)
        except Exception as e:
            raise VectorStoreError(f"Failed to connect to Qdrant: {e}") from e

        logger.info(
            "QdrantStore connected | url=%s collection=%s dim=%d",
            settings.qdrant_url, self.collection, self.vector_dim,
        )

    def ensure_collection(self, recreate: bool = False) -> None:
        """Create the collection if it does not yet exist, or recreate it."""
        qm = self._qmodels
        try:
            exists = self.client.collection_exists(collection_name=self.collection)
            if exists and recreate:
                logger.info("Recreating collection %s", self.collection)
                self.client.delete_collection(collection_name=self.collection)
                exists = False
            if not exists:
                logger.info("Creating collection %s (dim=%d)", self.collection, self.vector_dim)
                self.client.create_collection(
                    collection_name=self.collection,
                    vectors_config=qm.VectorParams(
                        size=self.vector_dim,
                        distance=qm.Distance.COSINE,
                    ),
                )
        except Exception as e:
            raise VectorStoreError(f"ensure_collection failed: {e}") from e

    def upsert(
        self,
        embeddings: Sequence[Sequence[float]],
        payloads: Sequence[dict],
    ) -> int:
        """Upsert vectors with payloads. Returns number of points written."""
        if len(embeddings) != len(payloads):
            raise VectorStoreError(
                f"embeddings and payloads length mismatch: "
                f"{len(embeddings)} vs {len(payloads)}"
            )
        if not embeddings:
            return 0

        qm = self._qmodels
        total = 0
        try:
            for i in range(0, len(embeddings), self.batch_size):
                batch_emb = embeddings[i : i + self.batch_size]
                batch_pl = payloads[i : i + self.batch_size]
                points = [
                    qm.PointStruct(
                        id=str(uuid.uuid4()),
                        vector=list(vec),
                        payload=dict(pl),
                    )
                    for vec, pl in zip(batch_emb, batch_pl)
                ]
                self.client.upsert(collection_name=self.collection, points=points)
                total += len(points)
            logger.info("Upserted %d points into %s", total, self.collection)
            return total
        except Exception as e:
            raise VectorStoreError(f"upsert failed: {e}") from e

    def search(
        self,
        query_vector: Sequence[float],
        top_k: int = 5,
    ) -> List[dict]:
        """Return the top_k most-similar payloads with their scores."""
        try:
            results = self.client.query_points(
                collection_name=self.collection,
                query=list(query_vector),
                limit=top_k,
                with_payload=True,
            ).points
        except Exception as e:
            raise VectorStoreError(f"search failed: {e}") from e

        return [
            {"score": float(p.score), "payload": p.payload or {}}
            for p in results
        ]

    def count(self) -> int:
        """Return number of points in the collection (0 if it doesn't exist)."""
        try:
            if not self.client.collection_exists(collection_name=self.collection):
                return 0
            return self.client.count(collection_name=self.collection, exact=True).count
        except Exception as e:
            logger.warning("count() failed: %s", e)
            return 0

    def delete_collection(self) -> None:
        """Drop the collection entirely (used by 'Reset' actions)."""
        try:
            if self.client.collection_exists(collection_name=self.collection):
                self.client.delete_collection(collection_name=self.collection)
                logger.info("Deleted collection %s", self.collection)
        except Exception as e:
            raise VectorStoreError(f"delete_collection failed: {e}") from e

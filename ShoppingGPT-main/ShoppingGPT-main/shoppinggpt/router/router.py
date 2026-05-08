"""Multi-intent semantic router backed by OpenAI embeddings.

Routes:
    products    – product search / availability / price questions
    policy      – return / shipping / warranty / store policy questions
    recommend   – open-ended "what should I wear / suggest me" requests
    chitchat    – casual conversation, greetings, off-topic questions

The router computes once-per-process embeddings for the canonical example
utterances per route and classifies new queries via cosine similarity.
A confidence threshold avoids forcing routing for ambiguous queries.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple

import numpy as np

from shoppinggpt.config import get_embeddings


PRODUCT_ROUTE_NAME = "products"
POLICY_ROUTE_NAME = "policy"
RECOMMEND_ROUTE_NAME = "recommend"
CHITCHAT_ROUTE_NAME = "chitchat"


PRODUCT_SAMPLES = [
    "how much does this dress cost",
    "what colors are available for this shirt",
    "is this pair of jeans in stock",
    "what clothing items do you have in your store",
    "show me white shirts",
    "do you have hoodies under 60 dollars",
    "find me a black dress in size M",
    "what is the price of product P010",
    "list all jackets",
    "how many units of P004 are left",
    "do you sell linen pants",
    "are there any red items in size L",
    "show me products for women under $80",
    "what cotton t-shirts do you have",
    "I'm looking for a leather jacket",
]

POLICY_SAMPLES = [
    "what is your return policy",
    "how long does shipping take",
    "can I exchange an item",
    "do you offer free shipping",
    "what is the warranty on this product",
    "how do I track my order",
    "what payment methods do you accept",
    "what is your refund policy",
    "do you ship internationally",
    "do you have a loyalty program",
    "how do I cancel an order",
    "is my data safe on your site",
]

RECOMMEND_SAMPLES = [
    "what should I wear to a wedding",
    "suggest an outfit for a date night",
    "recommend something for cold weather",
    "I need a gift for my girlfriend",
    "what looks good with black jeans",
    "help me pick a summer outfit",
    "I'm going to a job interview, what should I wear",
    "outfit ideas for the beach",
    "style me a casual weekend look",
    "what should I pair with a leather jacket",
]

CHITCHAT_SAMPLES = [
    "hello",
    "hi there",
    "how are you",
    "what's your name",
    "tell me a joke",
    "what's the weather like",
    "thank you",
    "goodbye",
    "who built you",
    "what can you do",
    "good morning",
    "nice to meet you",
]


@dataclass
class RouteSample:
    name: str
    utterances: List[str]
    embeddings: np.ndarray = field(default_factory=lambda: np.zeros((0, 0)))


def _cosine_matrix(query_vec: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """Cosine similarity between a single vector and a matrix of vectors."""
    q_norm = np.linalg.norm(query_vec) + 1e-9
    m_norm = np.linalg.norm(matrix, axis=1) + 1e-9
    return (matrix @ query_vec) / (m_norm * q_norm)


class SemanticRouter:
    """Cosine-similarity router over OpenAI embeddings."""

    def __init__(self, confidence_threshold: float = 0.18):
        self._threshold = confidence_threshold
        self._embeddings_client = get_embeddings()

        self._routes = [
            RouteSample(PRODUCT_ROUTE_NAME, PRODUCT_SAMPLES),
            RouteSample(POLICY_ROUTE_NAME, POLICY_SAMPLES),
            RouteSample(RECOMMEND_ROUTE_NAME, RECOMMEND_SAMPLES),
            RouteSample(CHITCHAT_ROUTE_NAME, CHITCHAT_SAMPLES),
        ]
        self._build_route_embeddings()

    def _build_route_embeddings(self) -> None:
        for route in self._routes:
            vectors = self._embeddings_client.embed_documents(route.utterances)
            route.embeddings = np.array(vectors, dtype=np.float32)

    def score(self, query: str) -> List[Tuple[str, float]]:
        query_vec = np.array(
            self._embeddings_client.embed_query(query), dtype=np.float32
        )
        scored: List[Tuple[str, float]] = []
        for route in self._routes:
            sims = _cosine_matrix(query_vec, route.embeddings)
            top_k = np.sort(sims)[-3:]  # average of top-3 to dampen noise
            scored.append((route.name, float(np.mean(top_k))))
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored

    def guide(self, query: str) -> str:
        if not query or not query.strip():
            return CHITCHAT_ROUTE_NAME
        scored = self.score(query)
        best_name, best_score = scored[0]
        runner_score = scored[1][1] if len(scored) > 1 else 0.0
        if best_score - runner_score < 0.02 and best_score < self._threshold:
            return CHITCHAT_ROUTE_NAME
        return best_name

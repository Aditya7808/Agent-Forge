from typing import List
import numpy as np
from shoppinggpt.config import get_embeddings
from shoppinggpt.router.lib_semantic_router import (
    PRODUCT_SAMPLE,
    CHITCHAT_SAMPLE,
    PRODUCT_ROUTE_NAME,
    CHITCHAT_ROUTE_NAME,
    _cosine_similarity,
)


class CosineSemanticRouter:
    """Alternative router using OpenAI embeddings with cosine similarity."""

    def __init__(self):
        embeddings = get_embeddings()
        self.product_embeddings = embeddings.embed_documents(PRODUCT_SAMPLE)
        self.chitchat_embeddings = embeddings.embed_documents(CHITCHAT_SAMPLE)

    def guide(self, query: str) -> str:
        query_emb = get_embeddings().embed_query(query)

        product_score = max(
            _cosine_similarity(query_emb, emb) for emb in self.product_embeddings
        )
        chitchat_score = max(
            _cosine_similarity(query_emb, emb) for emb in self.chitchat_embeddings
        )

        if product_score > chitchat_score:
            return PRODUCT_ROUTE_NAME
        return CHITCHAT_ROUTE_NAME

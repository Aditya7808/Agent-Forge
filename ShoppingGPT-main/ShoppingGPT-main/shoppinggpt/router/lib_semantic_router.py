from typing import List
import numpy as np
from shoppinggpt.config import get_embeddings

PRODUCT_SAMPLE = [
    "how much does this dress cost", "what colors are available for this shirt",
    "is this pair of jeans in stock", "what clothing items do you have in your store",
    "can you show me some shoes", "do you have any discounts on winter coats",
    "what's the warranty on this jacket", "are there any new clothing arrivals this week",
    "do you offer free shipping on clothes", "can I return this sweater if it doesn't fit",
    "what's your best-selling clothing item", "do you have any eco-friendly clothing options",
    "are these t-shirts made locally", "can you gift wrap this scarf",
    "what's the difference between these two styles of pants",
    "what's the material of this blouse", "do you have this dress in a larger size",
    "are these shoes suitable for running", "what's your return policy for online purchases",
    "can you recommend a good winter jacket", "do you have any sales on summer dresses",
    "do you offer alterations for pants", "what accessories would go well with this outfit",
    "do you have any vegan leather options", "what's the difference between slim fit and regular fit",
    "do you have any petite sizes available", "what's the latest fashion trend in your store",
    "do you have any waterproof jackets", "what's the price range for your formal wear",
    "can you help me find a dress for a wedding",
    "tìm áo sơ mi trắng", "giá bao nhiêu", "còn hàng không",
    "có size L không", "áo khoác da giá bao nhiêu",
    "tìm quần jean xanh", "váy hoa có màu gì", "đầm dự tiệc",
    "áo hoodie còn hàng không", "quần jogger size M",
    "shipping policy", "delivery time", "how to return items",
    "membership benefits", "payment methods accepted",
]

CHITCHAT_SAMPLE = [
    "do you like watching movies", "what's your favorite food",
    "the sky is so blue today", "how's the weather where you are",
    "do you have any hobbies", "tell me a joke",
    "what's your favorite book", "if you could travel anywhere, where would you go",
    "what's the meaning of life", "do you have any pets",
    "what's your favorite music genre", "how was your day",
    "what's your favorite season", "what's your favorite holiday",
    "what's your idea of a perfect day", "what's your favorite type of cuisine",
    "what's your favorite childhood memory", "what's your favorite sport to watch",
    "do you prefer mountains or beaches", "what's your favorite board game",
    "hello", "hi there", "hey", "good morning", "good evening",
    "xin chào", "chào bạn", "bạn khỏe không", "cảm ơn",
    "thank you", "bye", "goodbye", "see you later",
    "who are you", "what can you do", "help me",
    "tạm biệt", "hẹn gặp lại", "bạn tên gì",
]

PRODUCT_ROUTE_NAME = "products"
CHITCHAT_ROUTE_NAME = "chitchat"


def _cosine_similarity(a, b):
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


class SemanticRouter:
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

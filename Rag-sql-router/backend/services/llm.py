from functools import lru_cache
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from backend.config import settings


@lru_cache(maxsize=1)
def get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.openai_model,
        temperature=0,
        api_key=settings.openai_api_key,
        timeout=60,
        max_retries=2,
    )


@lru_cache(maxsize=1)
def get_classifier_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.openai_model,
        temperature=0,
        max_tokens=10,
        api_key=settings.openai_api_key,
        timeout=30,
        max_retries=2,
    )


@lru_cache(maxsize=1)
def get_embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model=settings.embedding_model,
        api_key=settings.openai_api_key,
        timeout=30,
        max_retries=2,
    )

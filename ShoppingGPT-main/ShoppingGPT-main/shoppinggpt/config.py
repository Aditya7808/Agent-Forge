"""Centralised configuration for ShoppingGPT.

All paths are resolved relative to the project root so the app runs
identically on Windows, macOS, and Linux. LLM and embedding clients
are configured against the OpenAI API.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError(
        "OPENAI_API_KEY is not set. Copy .env.example to .env and add your key."
    )

OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.2"))

DATA_DIR = PROJECT_ROOT / "data"
DATA_PRODUCT_PATH = str(DATA_DIR / "products.db")
DATA_TEXT_PATH = str(DATA_DIR / "policy.txt")
STORE_DIRECTORY = str(DATA_DIR / "datastore")

CURRENCY_CODE = os.getenv("CURRENCY_CODE", "USD")
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "auto")  # auto = mirror user
APP_NAME = os.getenv("APP_NAME", "ShoppingGPT")


def build_llm(temperature: float | None = None, streaming: bool = False) -> ChatOpenAI:
    return ChatOpenAI(
        model=OPENAI_CHAT_MODEL,
        temperature=OPENAI_TEMPERATURE if temperature is None else temperature,
        streaming=streaming,
        api_key=OPENAI_API_KEY,
    )


def build_embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(model=OPENAI_EMBEDDING_MODEL, api_key=OPENAI_API_KEY)


EMBEDDINGS = None  # lazy — built on first use to avoid import-time API calls


def get_embeddings() -> OpenAIEmbeddings:
    global EMBEDDINGS
    if EMBEDDINGS is None:
        EMBEDDINGS = build_embeddings()
    return EMBEDDINGS

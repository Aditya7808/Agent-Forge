"""Policy search tool.

Loads the company policy document into a FAISS vector store (built on
first run, cached on disk) and exposes a similarity-search tool the agent
can use to ground answers about returns, shipping, warranty, etc.
"""
from __future__ import annotations

import os
from typing import List

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.tools import tool
from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import FAISS

from shoppinggpt.config import DATA_TEXT_PATH, STORE_DIRECTORY, get_embeddings


_VECTORSTORE: FAISS | None = None


def _index_exists() -> bool:
    return os.path.exists(os.path.join(STORE_DIRECTORY, "index.faiss"))


def _load() -> FAISS:
    return FAISS.load_local(
        STORE_DIRECTORY,
        get_embeddings(),
        allow_dangerous_deserialization=True,
    )


def _build() -> FAISS:
    loader = TextLoader(DATA_TEXT_PATH, encoding="utf-8")
    documents = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=900, chunk_overlap=150)
    chunks = splitter.split_documents(documents)
    store = FAISS.from_documents(chunks, get_embeddings())
    os.makedirs(STORE_DIRECTORY, exist_ok=True)
    store.save_local(STORE_DIRECTORY)
    return store


def get_policy_store() -> FAISS:
    global _VECTORSTORE
    if _VECTORSTORE is None:
        _VECTORSTORE = _load() if _index_exists() else _build()
    return _VECTORSTORE


@tool
def policy_search_tool(query: str) -> str:
    """Search company policies (returns, shipping, warranty, payment, etc.).

    Use this tool whenever the user asks about how the store operates, not
    about a specific product."""
    try:
        store = get_policy_store()
        docs = store.similarity_search(query, k=4)
        if not docs:
            return "No relevant policy information was found."
        snippets: List[str] = []
        for idx, doc in enumerate(docs, 1):
            snippets.append(f"[{idx}] {doc.page_content.strip()}")
        return "\n\n".join(snippets)
    except Exception as err:  # noqa: BLE001
        return f"Error while searching policies: {err}"

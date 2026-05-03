"""FAISS-backed clause retriever with metadata filtering and a simple in-memory fallback."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

log = logging.getLogger("clauseai.retrievers")


class ClauseRetriever:
    """FAISS-backed retriever. Builds the index once on construction."""

    def __init__(self, json_path: str | Path, embedding_model: str = "text-embedding-3-small"):
        path = Path(json_path)
        if not path.exists():
            raise FileNotFoundError(f"Clause library not found at {path}")
        with open(path, "r", encoding="utf-8") as fh:
            self.library: List[Dict[str, Any]] = json.load(fh)

        self.docs: List[Document] = []
        for ct in self.library:
            for cl in ct["clauses"]:
                content = (
                    f"Contract Type: {ct['contract_type']}\n"
                    f"Clause: {cl['clause_title']}\n\n"
                    f"{cl['clause_text']}"
                )
                self.docs.append(Document(
                    page_content=content,
                    metadata={
                        "contract_type": ct["contract_type"],
                        "clause_title": cl["clause_title"],
                        "clause_text": cl["clause_text"],
                        **cl.get("metadata", {}),
                    },
                ))
        log.info("Loaded %d clauses across %d contract types", len(self.docs), len(self.library))

        self.embeddings = OpenAIEmbeddings(model=embedding_model)
        self.store = FAISS.from_documents(self.docs, self.embeddings)

    def by_contract_type(self, contract_type: str, k: int = 20) -> List[Dict[str, Any]]:
        return [
            {**d.metadata, "score": 1.0}
            for d in self.docs
            if d.metadata["contract_type"].lower() == contract_type.lower()
        ][:k]

    def similarity(self, query: str, contract_type: Optional[str] = None, k: int = 5) -> List[Dict[str, Any]]:
        results = self.store.similarity_search_with_score(query, k=k * 3 if contract_type else k)
        out = []
        allowed = {contract_type.lower(), "general clauses"} if contract_type else None
        for doc, score in results:
            if allowed and doc.metadata["contract_type"].lower() not in allowed:
                continue
            out.append({**doc.metadata, "score": float(score)})
            if len(out) >= k:
                break
        return out

    def expected_clause_titles(self, contract_type: str) -> List[str]:
        general = [
            d.metadata["clause_title"] for d in self.docs
            if d.metadata["contract_type"] == "General Clauses"
        ]
        specific = [
            d.metadata["clause_title"] for d in self.docs
            if d.metadata["contract_type"].lower() == contract_type.lower()
        ]
        return sorted(set(general + specific))

    def reference_clauses(self, contract_type: str, k: int = 12) -> List[Dict[str, Any]]:
        general = self.by_contract_type("General Clauses", k=k)
        specific = self.by_contract_type(contract_type, k=k)
        return general + specific

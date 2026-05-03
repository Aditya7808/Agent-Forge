"""File parsing and contract sectioning utilities."""
from __future__ import annotations

import io
import re
from typing import Any, Dict, List

import PyPDF2
import docx as docx_lib


SECTION_RE = re.compile(r"^\s*(\d+(?:\.\d+)*)[\.\)\s]+(.*)$", re.MULTILINE)


def load_pdf_bytes(data: bytes) -> str:
    reader = PyPDF2.PdfReader(io.BytesIO(data))
    parts = []
    for i, page in enumerate(reader.pages):
        parts.append(f"\n[Page {i+1}]\n{page.extract_text() or ''}")
    return "\n".join(parts).strip()


def load_docx_bytes(data: bytes) -> str:
    doc = docx_lib.Document(io.BytesIO(data))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def load_contract_bytes(filename: str, data: bytes) -> str:
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        return load_pdf_bytes(data)
    if name.endswith(".docx"):
        return load_docx_bytes(data)
    if name.endswith((".txt", ".md")):
        return data.decode("utf-8", errors="replace")
    raise ValueError(
        f"Unsupported file type: {filename}. Use .pdf, .docx, .txt, or .md."
    )


def split_into_sections(text: str) -> List[Dict[str, Any]]:
    matches = list(SECTION_RE.finditer(text))
    if not matches:
        return [{"id": "0", "title": "Full Document", "text": text}]
    out = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        out.append({
            "id": m.group(1),
            "title": m.group(2).strip()[:140],
            "text": text[start:end].strip(),
        })
    return out

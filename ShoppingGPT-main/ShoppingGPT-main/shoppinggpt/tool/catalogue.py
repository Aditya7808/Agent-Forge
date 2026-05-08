"""Direct catalogue access used by the Flask layer to render product cards.

These helpers do NOT take user-supplied SQL — they use parameterised
queries only. Use them from the API handler when you need structured
product data alongside the agent's natural-language answer."""
from __future__ import annotations

import re
import sqlite3
from typing import Any, Dict, List

from shoppinggpt.config import DATA_PRODUCT_PATH


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DATA_PRODUCT_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def fetch_by_codes(codes: List[str]) -> List[Dict[str, Any]]:
    if not codes:
        return []
    placeholders = ",".join("?" * len(codes))
    with _connect() as conn:
        rows = conn.execute(
            f"SELECT * FROM products WHERE product_code IN ({placeholders})",
            codes,
        ).fetchall()
    by_code = {row["product_code"]: dict(row) for row in rows}
    return [by_code[c] for c in codes if c in by_code]


def search_products(
    text: str | None = None,
    color: str | None = None,
    gender: str | None = None,
    max_price: int | None = None,
    limit: int = 8,
) -> List[Dict[str, Any]]:
    clauses: List[str] = ["stock_quantity > 0"]
    params: List[Any] = []
    if text:
        clauses.append(
            "(LOWER(product_name) LIKE ? OR LOWER(material) LIKE ? OR LOWER(brand) LIKE ?)"
        )
        like = f"%{text.lower()}%"
        params.extend([like, like, like])
    if color:
        clauses.append("LOWER(color) LIKE ?")
        params.append(f"%{color.lower()}%")
    if gender:
        clauses.append("LOWER(gender) LIKE ?")
        params.append(f"%{gender.lower()}%")
    if max_price is not None:
        clauses.append("price <= ?")
        params.append(max_price)

    sql = (
        "SELECT * FROM products WHERE "
        + " AND ".join(clauses)
        + " ORDER BY stock_quantity DESC LIMIT ?"
    )
    params.append(limit)
    with _connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(row) for row in rows]


_CODE_RE = re.compile(r"\b(P\d{3})\b")


def extract_product_codes(text: str) -> List[str]:
    """Pull product_code references like P001 out of free-form agent text."""
    seen: List[str] = []
    for code in _CODE_RE.findall(text or ""):
        if code not in seen:
            seen.append(code)
    return seen

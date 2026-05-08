"""Product search tool.

Translates natural-language product questions into a guarded SELECT query
against the local SQLite catalogue. The LLM only ever produces a SELECT
statement; the executor refuses anything else, which keeps the agent safe
even if the model attempts a destructive action.
"""
from __future__ import annotations

import re
import sqlite3
from contextlib import contextmanager
from typing import Any, Dict, Iterator, List

from langchain_core.prompts import PromptTemplate
from langchain_core.tools import tool
from langchain_core.runnables import RunnablePassthrough

from shoppinggpt.config import DATA_PRODUCT_PATH, build_llm

PRODUCT_RECOMMENDATION_PROMPT = """You are a SQL generator for a fashion retail
SQLite database. Translate the user's natural-language request into one
SELECT statement.

Schema — table `products`:
    product_code     TEXT     -- unique identifier (e.g. P001)
    product_name     TEXT     -- product name in English
    material         TEXT     -- e.g. cotton, denim, silk
    size             TEXT     -- comma-separated sizes
    color            TEXT     -- comma-separated colors
    brand            TEXT
    gender           TEXT     -- Men | Women | Unisex
    stock_quantity   INTEGER
    price            INTEGER  -- USD

Rules:
- Output ONLY the SQL. No prose. No markdown fences. No trailing semicolon.
- Use case-insensitive LIKE for text searches: LOWER(column) LIKE LOWER('%term%').
- Always limit results to 12 rows: append `LIMIT 12`.
- Never write INSERT, UPDATE, DELETE, DROP, ALTER, ATTACH, PRAGMA, or VACUUM.
- Order by stock_quantity DESC unless the user asks otherwise.

Question: {input}
SQL:"""

_DENY_RE = re.compile(
    r"\b(insert|update|delete|drop|alter|attach|detach|pragma|vacuum|replace|create)\b",
    re.IGNORECASE,
)


def _is_safe_select(query: str) -> bool:
    stripped = query.strip().rstrip(";").strip()
    if not stripped:
        return False
    if not stripped.lower().startswith("select"):
        return False
    return _DENY_RE.search(stripped) is None


def _clean_sql(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:sql)?", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    return cleaned.rstrip(";").strip()


@contextmanager
def _connect(db_path: str) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def execute_product_query(sql: str) -> List[Dict[str, Any]]:
    if not _is_safe_select(sql):
        raise ValueError("Refused: only single-statement SELECT queries are allowed.")
    with _connect(DATA_PRODUCT_PATH) as conn:
        cursor = conn.execute(sql)
        return [dict(row) for row in cursor.fetchall()]


def format_products(rows: List[Dict[str, Any]]) -> str:
    if not rows:
        return "No matching products were found in the catalogue."
    lines = []
    for row in rows:
        price = row.get("price")
        price_str = f"${int(price):,}" if isinstance(price, (int, float)) else "n/a"
        lines.append(
            f"- [{row.get('product_code')}] {row.get('product_name')} | "
            f"{row.get('color') or 'n/a'} | size: {row.get('size') or 'n/a'} | "
            f"{row.get('material') or 'n/a'} | brand: {row.get('brand') or 'n/a'} | "
            f"stock: {row.get('stock_quantity', 0)} | price: {price_str}"
        )
    return "\n".join(lines)


@tool
def product_search_tool(query: str) -> str:
    """Search the product catalogue for items matching the user's request.

    Use this tool whenever the user asks about specific products, prices,
    colours, sizes, stock, or to filter the catalogue. Pass the user's
    request verbatim; the tool will translate it into SQL and return a
    formatted list of matching products."""
    try:
        llm = build_llm(temperature=0)
        prompt = PromptTemplate(
            template=PRODUCT_RECOMMENDATION_PROMPT, input_variables=["input"]
        )
        chain = (
            {"input": RunnablePassthrough()}
            | prompt
            | llm
            | (lambda msg: _clean_sql(msg.content))
        )
        sql = chain.invoke(query)
        rows = execute_product_query(sql)
        return format_products(rows)
    except ValueError as err:
        return f"Could not run that search: {err}"
    except sqlite3.Error as err:
        return f"Database error while searching: {err}"
    except Exception as err:  # noqa: BLE001 — surface to the agent, not the user
        return f"Unexpected error during product search: {err}"

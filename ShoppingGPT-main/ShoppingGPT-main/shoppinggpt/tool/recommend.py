"""Outfit recommendation tool.

Pulls the product catalogue and asks the LLM to compose a curated
recommendation grounded in real inventory. This stops the agent from
hallucinating products that don't exist."""
from __future__ import annotations

import sqlite3
from typing import Any, Dict, List

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool

from shoppinggpt.config import DATA_PRODUCT_PATH, build_llm

_RECOMMEND_PROMPT = """You are a fashion stylist for an online store. Using
ONLY the products listed below, propose a thoughtful recommendation for the
user. Cite each product by its product_code in square brackets, e.g. [P004].
Do not invent products. If the user asks for an outfit, suggest 2–4 items
that work together. Reply in English.

Available products:
{catalogue}

User request: {request}

Recommendation:"""


def _load_catalogue(limit: int = 60) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DATA_PRODUCT_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT product_code, product_name, material, size, color, brand, "
            "gender, stock_quantity, price FROM products "
            "WHERE stock_quantity > 0 ORDER BY stock_quantity DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def _format_catalogue(rows: List[Dict[str, Any]]) -> str:
    return "\n".join(
        f"[{r['product_code']}] {r['product_name']} — {r['color']}, "
        f"size {r['size']}, {r['gender']}, ${int(r['price']):,}, "
        f"stock {r['stock_quantity']}"
        for r in rows
    )


@tool
def outfit_recommendation_tool(request: str) -> str:
    """Recommend outfits or product combinations from real inventory.

    Use when the user asks for styling advice, outfit ideas, gift
    suggestions, or open-ended "what should I buy" questions."""
    try:
        rows = _load_catalogue()
        if not rows:
            return "The catalogue is currently empty — no recommendations available."
        catalogue = _format_catalogue(rows)
        prompt = ChatPromptTemplate.from_template(_RECOMMEND_PROMPT)
        chain = prompt | build_llm(temperature=0.4)
        response = chain.invoke({"catalogue": catalogue, "request": request})
        return response.content
    except Exception as err:  # noqa: BLE001
        return f"Error while building a recommendation: {err}"

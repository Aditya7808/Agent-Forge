import sqlite3
from typing import Union, List, Dict

from langchain.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain.tools import tool
from langchain_openai import ChatOpenAI

from shoppinggpt.config import OPENAI_API_KEY, DATA_PRODUCT_PATH

PRODUCT_RECOMMENDATION_PROMPT = """You are a SQL expert for a fashion store database.
Generate a single SQLite query for the user's request.

The 'products' table has these columns:
- product_code (TEXT, primary key)
- product_name (TEXT)
- material (TEXT)
- size (TEXT, comma-separated e.g. "S, M, L, XL")
- color (TEXT, comma-separated e.g. "Đen, Trắng")
- brand (TEXT)
- gender (TEXT: Nam/Nữ/Unisex)
- stock_quantity (INTEGER)
- price (REAL, in VND)

Rules:
- Use LIKE with % for partial text matches (case-insensitive).
- For size/color searches, use LIKE since values are comma-separated.
- Only SELECT queries are allowed. Never INSERT, UPDATE, DELETE, or DROP.
- Output ONLY the raw SQL query. No markdown, no backticks, no explanation.

Question: {input}
"""


class ProductDataLoader:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def connect(self):
        self.conn = sqlite3.connect(self.db_path)

    def close(self):
        if self.conn:
            self.conn.close()

    @staticmethod
    def clean_sql_query(query: str) -> str:
        cleaned = query.strip()
        for wrapper in ["```sql", "```SQL", "```"]:
            cleaned = cleaned.replace(wrapper, "")
        return cleaned.strip()

    def execute_query(self, query: str) -> List[Dict]:
        if not self.conn:
            self.connect()
        cleaned = self.clean_sql_query(query)
        forbidden = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE"]
        upper = cleaned.upper()
        for keyword in forbidden:
            if keyword in upper:
                raise ValueError(f"Forbidden SQL operation: {keyword}")
        cursor = self.conn.cursor()
        cursor.execute(cleaned)
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


@tool
def product_search_tool(input: str) -> Union[List[Dict], str]:
    """Search for product information in the store database using natural language.

    Args:
        input: Natural language query about products (price, color, size, brand, etc.)

    Returns:
        List of matching products or an error message.
    """
    try:
        llm = ChatOpenAI(
            temperature=0,
            model="gpt-4o-mini",
            api_key=OPENAI_API_KEY,
        )
        prompt = PromptTemplate(
            template=PRODUCT_RECOMMENDATION_PROMPT,
            input_variables=["input"],
        )

        with ProductDataLoader(DATA_PRODUCT_PATH) as loader:
            chain = (
                {"input": RunnablePassthrough()}
                | prompt
                | llm
                | (lambda x: loader.execute_query(x.content))
            )
            return chain.invoke(input)
    except Exception as e:
        return f"Product search error: {e}"

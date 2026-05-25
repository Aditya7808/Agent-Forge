import re
import logging
from langchain_community.utilities import SQLDatabase
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from sqlalchemy import text
from backend.config import settings
from backend.services.llm import get_llm

logger = logging.getLogger(__name__)

_db: SQLDatabase | None = None

SQL_GENERATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert SQLite SQL query generator.

Database Schema:
{schema}

Rules:
1. Generate ONLY the SQL query, no explanations, no markdown.
2. Use SQLite syntax.
3. Always use exact column names from the schema.
4. For text comparisons, use LIKE with % for partial matches.
5. ONLY use SELECT statements - never DELETE, DROP, UPDATE, INSERT, ALTER, CREATE.
6. Return useful, readable results with appropriate LIMIT clauses where helpful."""),
    ("user", "{question}")
])

SQL_SYNTHESIS_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a helpful data analyst. Given a user question, the SQL query used, and the results, provide a clear, concise natural language answer.

Be specific and reference the actual numbers from the results."""),
    ("user", "Question: {question}\n\nSQL Query:\n{sql}\n\nResults:\n{results}")
])


def get_db() -> SQLDatabase:
    global _db
    if _db is None:
        _db = SQLDatabase.from_uri(
            f"sqlite:///{settings.database_path}",
            sample_rows_in_table_info=3,
        )
    return _db


def _clean_sql(sql: str) -> str:
    sql = re.sub(r"^```(?:sql)?\s*", "", sql.strip(), flags=re.IGNORECASE)
    sql = re.sub(r"```\s*$", "", sql.strip())
    return sql.strip().rstrip(";")


def _is_safe_select(sql: str) -> bool:
    upper = sql.upper().strip()
    if not upper.startswith("SELECT") and not upper.startswith("WITH"):
        return False
    forbidden = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE", "TRUNCATE", "REPLACE", "ATTACH"]
    tokens = re.split(r"\s+|;", upper)
    return not any(tok in forbidden for tok in tokens)


def run_sql_chain(question: str) -> dict:
    db = get_db()
    llm = get_llm()

    schema = db.get_table_info()

    generation_chain = (
        SQL_GENERATION_PROMPT
        | llm
        | StrOutputParser()
        | _clean_sql
    )

    sql_query = generation_chain.invoke({"schema": schema, "question": question})
    logger.info(f"Generated SQL: {sql_query}")

    if not _is_safe_select(sql_query):
        return {
            "response": "I generated a query that wasn't a safe read-only SELECT. Please rephrase your question.",
            "sql_query": sql_query,
            "data": [],
            "error": "unsafe_sql"
        }

    try:
        from sqlalchemy import create_engine
        engine = create_engine(f"sqlite:///{settings.database_path}")
        with engine.connect() as conn:
            result = conn.execute(text(sql_query))
            rows = result.fetchall()
            columns = list(result.keys())
        data = [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        logger.exception("SQL execution failed")
        return {
            "response": f"SQL execution error: {str(e)}",
            "sql_query": sql_query,
            "data": [],
            "error": str(e)
        }

    if not data:
        return {
            "response": "The query ran successfully, but no rows matched your criteria.",
            "sql_query": sql_query,
            "data": []
        }

    results_str = "\n".join(str(row) for row in data[:20])

    synthesis_chain = SQL_SYNTHESIS_PROMPT | llm | StrOutputParser()
    answer = synthesis_chain.invoke({
        "question": question,
        "sql": sql_query,
        "results": results_str
    })

    return {
        "response": answer,
        "sql_query": sql_query,
        "data": data[:50],
    }

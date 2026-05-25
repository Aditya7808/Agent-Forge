from openai import OpenAI
from sqlalchemy import create_engine, text, inspect
from backend.config import settings

engine = create_engine(f"sqlite:///{settings.database_path}")


def get_schema_info() -> str:
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    schema_parts = []
    for table in tables:
        columns = inspector.get_columns(table)
        col_defs = ", ".join([f"{c['name']} ({c['type']})" for c in columns])
        schema_parts.append(f"Table: {table} | Columns: {col_defs}")
    return "\n".join(schema_parts)


SQL_SYSTEM_PROMPT = """You are an expert SQL query generator. Given a natural language question about a SQLite database, generate the appropriate SQL query.

Database Schema:
{schema}

Rules:
1. Generate ONLY the SQL query, no explanations
2. Use SQLite syntax
3. Always use exact column names from the schema
4. For text comparisons, use LIKE with % for partial matches
5. Return useful, readable results
6. Never use DELETE, DROP, UPDATE, INSERT, or any data-modifying statements
7. Only use SELECT statements"""


def generate_sql(query: str) -> str:
    client = OpenAI(api_key=settings.openai_api_key)
    schema = get_schema_info()

    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": SQL_SYSTEM_PROMPT.format(schema=schema)},
            {"role": "user", "content": query}
        ],
        temperature=0,
        max_tokens=500,
    )

    sql = response.choices[0].message.content.strip()
    sql = sql.replace("```sql", "").replace("```", "").strip()
    return sql


def execute_sql(sql: str) -> dict:
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        rows = result.fetchall()
        columns = list(result.keys())
    return {"rows": rows, "columns": columns}


def natural_language_to_sql_response(query: str) -> dict:
    sql = generate_sql(query)

    try:
        result = execute_sql(sql)
    except Exception as e:
        return {
            "response": f"I generated a SQL query but encountered an error: {str(e)}",
            "sql_query": sql,
            "error": True
        }

    rows = result["rows"]
    columns = result["columns"]

    if not rows:
        return {
            "response": "No results found for your query.",
            "sql_query": sql,
            "data": []
        }

    client = OpenAI(api_key=settings.openai_api_key)
    data_str = "\n".join([str(dict(zip(columns, row))) for row in rows[:20]])

    synthesis_response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": "You are a helpful data analyst. Given the user's question and the SQL query results, provide a clear, natural language answer. Be concise but informative."},
            {"role": "user", "content": f"Question: {query}\n\nSQL Query: {sql}\n\nResults:\n{data_str}"}
        ],
        temperature=0.3,
        max_tokens=500,
    )

    return {
        "response": synthesis_response.choices[0].message.content.strip(),
        "sql_query": sql,
        "data": [dict(zip(columns, row)) for row in rows[:50]]
    }

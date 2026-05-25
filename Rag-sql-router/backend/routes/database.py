from fastapi import APIRouter, HTTPException
from sqlalchemy import create_engine, text
from backend.models import DatabaseQueryRequest, DatabaseQueryResponse, DatabaseStatsResponse
from backend.config import settings

router = APIRouter(prefix="/api/database", tags=["database"])

engine = create_engine(f"sqlite:///{settings.database_path}")


@router.get("/stats", response_model=DatabaseStatsResponse)
async def get_stats():
    try:
        with engine.connect() as conn:
            cities = conn.execute(text("SELECT COUNT(*) FROM city_stats")).scalar()
            population = conn.execute(text("SELECT SUM(population) FROM city_stats")).scalar()
            states = conn.execute(text("SELECT COUNT(DISTINCT state) FROM city_stats")).scalar()
            avg_pop = conn.execute(text("SELECT AVG(population) FROM city_stats")).scalar()

            top_cities_result = conn.execute(
                text("SELECT city_name, population, state FROM city_stats ORDER BY population DESC LIMIT 10")
            ).fetchall()
            top_cities = [{"city": r[0], "population": r[1], "state": r[2]} for r in top_cities_result]

            state_dist_result = conn.execute(
                text("SELECT state, COUNT(*) as count FROM city_stats GROUP BY state ORDER BY count DESC LIMIT 10")
            ).fetchall()
            state_distribution = [{"state": r[0], "count": r[1]} for r in state_dist_result]

        return DatabaseStatsResponse(
            total_cities=cities or 0,
            total_population=population or 0,
            total_states=states or 0,
            avg_population=int(avg_pop or 0),
            top_cities=top_cities,
            state_distribution=state_distribution,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data")
async def get_all_data():
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT city_name, population, state FROM city_stats ORDER BY population DESC"))
            rows = result.fetchall()
            columns = list(result.keys())
        return {
            "data": [dict(zip(columns, row)) for row in rows],
            "columns": columns,
            "row_count": len(rows)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query", response_model=DatabaseQueryResponse)
async def run_query(request: DatabaseQueryRequest):
    sql = request.query.strip()

    forbidden = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE"]
    for keyword in forbidden:
        if keyword in sql.upper().split():
            raise HTTPException(status_code=400, detail="Only SELECT queries are allowed")

    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            rows = result.fetchall()
            columns = list(result.keys())

        return DatabaseQueryResponse(
            data=[dict(zip(columns, row)) for row in rows],
            columns=columns,
            row_count=len(rows)
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Query error: {str(e)}")

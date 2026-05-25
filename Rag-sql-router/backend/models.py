from pydantic import BaseModel
from typing import Optional
from enum import Enum


class RouteType(str, Enum):
    SQL = "sql"
    RAG = "rag"


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    route_used: RouteType
    trust_score: Optional[float] = None
    sql_query: Optional[str] = None
    metadata: Optional[dict] = None


class DocumentUploadResponse(BaseModel):
    message: str
    files_processed: int
    session_id: str


class DatabaseQueryRequest(BaseModel):
    query: str


class DatabaseQueryResponse(BaseModel):
    data: list
    columns: list
    row_count: int


class DatabaseStatsResponse(BaseModel):
    total_cities: int
    total_population: int
    total_states: int
    avg_population: int
    top_cities: list
    state_distribution: list


class HealthResponse(BaseModel):
    status: str
    version: str
    services: dict

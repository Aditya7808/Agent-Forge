from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config import settings
from backend.models import HealthResponse
from backend.routes import chat, documents, database

app = FastAPI(
    title="RAG + SQL Router API",
    description="Intelligent query routing between SQL database and document retrieval with trust scoring",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(documents.router)
app.include_router(database.router)


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    services = {
        "openai": bool(settings.openai_api_key),
        "codex": bool(settings.codex_api_key),
        "database": True,
        "chromadb": True,
    }
    return HealthResponse(
        status="healthy" if services["openai"] else "degraded",
        version="2.0.0",
        services=services,
    )


@app.get("/")
async def root():
    return {"message": "RAG + SQL Router API", "docs": "/docs"}

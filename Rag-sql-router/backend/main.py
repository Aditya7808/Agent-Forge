import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config import settings
from backend.models import HealthResponse
from backend.routes import chat, documents, database
from backend.graph import get_workflow

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting RAG + SQL Router API")
    logger.info(f"OpenAI model: {settings.openai_model}")
    logger.info(f"Embedding model: {settings.embedding_model}")
    logger.info(f"Database: {settings.database_path}")
    logger.info(f"Chroma persist dir: {settings.chroma_persist_dir}")

    try:
        get_workflow()
        logger.info("LangGraph workflow ready")
    except Exception as e:
        logger.error(f"Failed to compile workflow at startup: {e}")

    yield
    logger.info("Shutting down RAG + SQL Router API")


app = FastAPI(
    title="RAG + SQL Router API",
    description="Intelligent query routing (LangChain + LangGraph) between SQL and RAG with trust scoring",
    version="2.0.0",
    lifespan=lifespan,
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
        "codex": bool(settings.codex_api_key) and not settings.codex_api_key.startswith("your-"),
        "database": True,
        "chromadb": True,
        "langgraph": True,
    }
    return HealthResponse(
        status="healthy" if services["openai"] else "degraded",
        version="2.0.0",
        services=services,
    )


@app.get("/")
async def root():
    return {"message": "RAG + SQL Router API", "docs": "/docs"}

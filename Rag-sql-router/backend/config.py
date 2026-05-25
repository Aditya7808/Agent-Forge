import os
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str = ""
    codex_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    chroma_persist_dir: str = "./chroma_db"
    database_path: str = str(Path(__file__).parent / "data" / "city_database.sqlite")
    upload_dir: str = str(Path(__file__).parent / "uploads")
    max_upload_size_mb: int = 50
    similarity_top_k: int = 3
    cors_origins: list = ["http://localhost:5173", "http://localhost:3000"]

    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()

os.makedirs(settings.upload_dir, exist_ok=True)
os.makedirs(settings.chroma_persist_dir, exist_ok=True)

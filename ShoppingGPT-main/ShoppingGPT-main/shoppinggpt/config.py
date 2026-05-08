import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

DATA_PRODUCT_PATH = str(DATA_DIR / "products.db")
DATA_TEXT_PATH = str(DATA_DIR / "policy.txt")
STORE_DIRECTORY = str(DATA_DIR / "datastore")

_embeddings_instance = None


def get_embeddings():
    global _embeddings_instance
    if _embeddings_instance is None:
        from langchain_openai import OpenAIEmbeddings
        _embeddings_instance = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=OPENAI_API_KEY,
        )
    return _embeddings_instance

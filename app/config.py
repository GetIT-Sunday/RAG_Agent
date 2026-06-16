import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'knowledge.db'}")
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "BAAI/bge-small-zh-v1.5")
ENABLE_EMBEDDING_FALLBACK = os.getenv("ENABLE_EMBEDDING_FALLBACK", "true").lower() == "true"
ALLOW_MODEL_DOWNLOAD = os.getenv("ALLOW_MODEL_DOWNLOAD", "false").lower() == "true"
FORCE_EMBEDDING_FALLBACK = os.getenv("FORCE_EMBEDDING_FALLBACK", "false").lower() == "true"
SEARCH_TIMEOUT_SECONDS = int(os.getenv("SEARCH_TIMEOUT_SECONDS", "90"))
VECTOR_WEIGHT = 0.75
KEYWORD_WEIGHT = 0.25
MIN_RELEVANCE_SCORE = float(os.getenv("MIN_RELEVANCE_SCORE", "0.05"))

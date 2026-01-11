import os
from dotenv import load_dotenv

# Load .env from repository root (if present)
load_dotenv()


class Settings:
    project_name: str = "RAG Knowledge Base API"
    chroma_persist_dir: str = os.getenv("CHROMA_PERSIST_DIR", "chroma_db")
    embed_model: str = os.getenv("EMBED_MODEL", "text-embedding-3-small")
    # gemini_api_key: str = os.getenv("GEMINI_API_KEY", "test")
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4o")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/rag_kb"
    )


settings = Settings()

# Convenient module-level constants for importers
CHROMA_PERSIST_DIR = settings.chroma_persist_dir
EMBED_MODEL = settings.embed_model
# GEMINI_API_KEY = settings.gemini_api_key
LLM_MODEL = settings.llm_model
OPENAI_API_KEY = settings.openai_api_key
DATABASE_URL = settings.database_url

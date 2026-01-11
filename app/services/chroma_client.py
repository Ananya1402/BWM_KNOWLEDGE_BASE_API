# services/chroma_client.py
import chromadb
from chromadb.config import Settings
import httpx
from openai import OpenAI
from app.core import config

_settings = Settings(anonymized_telemetry=False, allow_reset=True)

chroma_client = chromadb.PersistentClient(
    path=config.CHROMA_PERSIST_DIR,
    settings=_settings
)

_openai_client = None


def _get_openai_client():
    """Lazy initialize OpenAI client with custom httpx client"""
    global _openai_client

    if _openai_client is None:
        try:
            http_client = httpx.Client(
                timeout=60.0,
                follow_redirects=True
            )

            _openai_client = OpenAI(
                api_key=config.OPENAI_API_KEY,
                http_client=http_client
            )
        except Exception as e:
            import logging
            logger = logging.getLogger("app.chroma_client")
            logger.error(f"Failed to initialize OpenAI client: {e}")
            raise

    return _openai_client


def get_openai_client():
    """Public function to get OpenAI client"""
    return _get_openai_client()


def get_embedding(text: str) -> list:
    """Get embedding for text using OpenAI"""
    client = _get_openai_client()

    response = client.embeddings.create(
        model=config.EMBED_MODEL,
        input=text
    )

    return response.data[0].embedding

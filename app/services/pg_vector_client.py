# services/pg_vector_client.py
import httpx
from openai import OpenAI
from app.core import config
from sqlalchemy.orm import Session
from typing import List

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
            logger = logging.getLogger("app.pg_vector_client")
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


# ===== PGVECTOR HELPER FUNCTIONS =====

def store_embeddings_batch(
    db: Session,
    chunks: List[str],
    embeddings: List[List[float]],
    document_id: str
) -> int:
    """
    Store embeddings in PostgreSQL using pgvector.
    Documents are shared across all sessions.
    Returns the number of embeddings stored.
    """
    from app.db.models import Chunk, Embedding
    import uuid
    
    try:
        stored_count = 0
        
        for idx, (chunk_text, embedding_vector) in enumerate(zip(chunks, embeddings)):
            # Create chunk
            chunk = Chunk(
                id=uuid.uuid4(),
                document_id=uuid.UUID(document_id),
                content=chunk_text,
                chunk_index=idx
            )
            db.add(chunk)
            db.flush()  # Get the chunk ID
            
            # Create embedding
            text_preview = chunk_text[:200] if len(chunk_text) > 200 else chunk_text
            embedding_obj = Embedding(
                chunk_id=chunk.id,
                document_id=uuid.UUID(document_id),
                embedding=embedding_vector,
                embedding_model=config.EMBED_MODEL,
                text_preview=text_preview
            )
            db.add(embedding_obj)
            stored_count += 1
        
        db.commit()
        return stored_count
    except Exception as e:
        import logging
        logger = logging.getLogger("app.pg_vector_client")
        logger.error(f"Failed to store embeddings: {e}", exc_info=True)
        db.rollback()
        raise


def similarity_search(
    db: Session,
    query_embedding: List[float],
    k: int = 4
) -> tuple[List[str], List[str]]:
    """
    Perform similarity search using pgvector cosine distance.
    Searches across ALL documents (not session-specific).
    Returns (documents, sources) tuple.
    """
    from app.db.models import Embedding, Chunk, Document
    from sqlalchemy import text
    import uuid
    
    try:
        # Build the query - search ALL documents
        query = db.query(
            Chunk.content,
            Document.filename,
            Embedding.embedding.cosine_distance(query_embedding).label('distance')
        ).join(
            Embedding, Chunk.id == Embedding.chunk_id
        ).join(
            Document, Chunk.document_id == Document.id
        )
        
        # Order by similarity and limit
        results = query.order_by('distance').limit(k).all()
        
        documents = [r[0] for r in results]  # content
        sources = [r[1] for r in results]    # filename
        
        return documents, sources
    except Exception as e:
        import logging
        logger = logging.getLogger("app.pg_vector_client")
        logger.error(f"Similarity search failed: {e}", exc_info=True)
        return [], []

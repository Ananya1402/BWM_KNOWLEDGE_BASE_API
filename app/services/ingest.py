# services/ingest.py
import os
import logging
import uuid
from typing import List, Optional
from pypdf import PdfReader
from sqlalchemy.orm import Session
from app.services import status as job_status
from app.services.pg_vector_client import get_embedding, store_embeddings_batch
from app.db.models import Document, Collection
from app.db.database import SessionLocal

logger = logging.getLogger("app.ingest")


def _read_pdf_text(file_path: str) -> str:
    reader = PdfReader(file_path)
    return "\n".join([p.extract_text() or "" for p in reader.pages])


def _chunk_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 100) -> List[str]:
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end].strip())
        start = max(end - chunk_overlap, end)

    return [c for c in chunks if c]


def ingest_pdf_file(
    file_path: str,
    collection_name: str = "default",
    job_id: Optional[str] = None
):
    """
    Ingest PDF file into pgvector database.
    Documents are shared across all sessions - no session_id required.
    """
    db = SessionLocal()
    
    try:
        if job_id:
            job_status.set_status(job_id, "running")

        logger.info("--- STEP 1: Reading PDF ---")
        text = _read_pdf_text(file_path)
        chunks = _chunk_text(text)

        filename = os.path.basename(file_path)

        # ===== PGVECTOR INGESTION =====
        logger.info("--- STEP 2: Getting or creating Collection ---")
        
        # Get or create collection
        collection = db.query(Collection).filter(Collection.name == collection_name).first()
        if not collection:
            collection = Collection(
                id=uuid.uuid4(),
                name=collection_name,
                description=f"Auto-created collection for {collection_name}"
            )
            db.add(collection)
            db.commit()
            db.refresh(collection)
            logger.info(f"Created new collection: {collection_name}")
        else:
            logger.info(f"Using existing collection: {collection_name}")
        
        logger.info("--- STEP 3: Creating Document record ---")
        document = Document(
            id=uuid.uuid4(),
            collection_id=collection.id,
            filename=filename,
            document_type="pdf",
            title=filename
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        
        logger.info(f"Created document with ID: {document.id} in collection '{collection_name}'")
        
        logger.info("--- STEP 4: Computing embeddings and storing in pgvector ---")
        embeddings = [get_embedding(chunk) for chunk in chunks]
        
        stored_count = store_embeddings_batch(
            db=db,
            chunks=chunks,
            embeddings=embeddings,
            document_id=str(document.id)
        )
        
        logger.info(f"Stored {stored_count} embeddings in pgvector")
        # ===== END PGVECTOR =====

        logger.info("--- STEP 5: Finalizing ---")
        if job_id:
            job_status.set_status(job_id, "completed")

        logger.info("Ingest successful for %s", filename)

    except Exception as e:
        logger.error("!!! INGEST CRASHED: %s", str(e), exc_info=True)

        if job_id:
            job_status.set_status(job_id, "failed")

    finally:
        db.close()
        if os.path.exists(file_path):
            os.remove(file_path)

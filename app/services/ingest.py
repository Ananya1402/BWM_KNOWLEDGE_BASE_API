# services/ingest.py
import os
import logging
from typing import List, Optional
from pypdf import PdfReader
from app.services import status as job_status
from app.services.chroma_client import chroma_client, get_embedding

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


def ingest_pdf_file(file_path: str, collection_name: str = "default", job_id: Optional[str] = None):
    try:
        if job_id:
            job_status.set_status(job_id, "running")

        logger.info("--- STEP 1: Reading PDF ---")
        text = _read_pdf_text(file_path)
        chunks = _chunk_text(text)

        logger.info("--- STEP 2: Getting Collection ---")
        collection = chroma_client.get_or_create_collection(
            name=collection_name
        )

        filename = os.path.basename(file_path)
        ids = [f"{filename}-{i}" for i in range(len(chunks))]
        metadatas = [{"source": filename} for _ in chunks]

        logger.info("--- STEP 3: Computing embeddings and writing to disk ---")
        embeddings = [get_embedding(chunk) for chunk in chunks]

        collection.add(
            ids=ids,
            documents=chunks,
            embeddings=embeddings,
            metadatas=metadatas
        )

        logger.info("--- STEP 4: Finalizing ---")
        if job_id:
            job_status.set_status(job_id, "completed")

        logger.info("Ingest successful for %s", filename)

    except Exception as e:
        logger.error("!!! INGEST CRASHED: %s", str(e), exc_info=True)

        if job_id:
            job_status.set_status(job_id, "failed")

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

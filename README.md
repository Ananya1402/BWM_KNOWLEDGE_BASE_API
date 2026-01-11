# RAG Knowledge Base API

FastAPI skeleton for a Retrieval-Augmented Generation (RAG) framework.

Quick start

1. Install dependencies (prefer a venv):

```bash
pip install -r requirements.txt
```

2. Set environment variables:

```bash
set GEMINI_API_KEY=your_key_here
set CHROMA_PERSIST_DIR=./chroma_db
```

3. Run the app:

```bash
uvicorn app.main:app --reload
```

Endpoints

- `POST /api/ingest` — upload a PDF file (background ingestion)
- `POST /api/query` — query the vector DB and get an answer

Notes

- This is a minimal skeleton; for production replace background tasks with a queue, secure endpoints, and add auth.  
- Files created: `app/main.py`, `app/api/routes.py`, `app/services/ingest.py`, `app/services/qa.py`, `app/schemas/schemas.py`, `app/core/config.py`, `app/logging_config.py`.
# BWM_KNOWLEDGE_BASE_API
Knowledge Base API Framework based on RAG

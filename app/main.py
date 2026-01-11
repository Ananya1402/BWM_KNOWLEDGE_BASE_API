# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.logging_config import configure_logging
from app.core.config import settings
from app.db.database import engine, Base
from app.db.models import ChatMessage, ChatSession  # Import to register models

configure_logging()

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.project_name, version="0.1.0")

# Basic CORS for web usage in QA widgets; adjust in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}


# python -m uvicorn app.main:app --reload --reload-exclude "chroma_db/*t 127.0.0.1 --port 8000

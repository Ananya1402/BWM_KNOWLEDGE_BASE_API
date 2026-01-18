from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException, Depends, Form, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from uuid import UUID

from app.schemas.schemas import (
    UploadResponse,
    QueryRequest,
    QueryResponse,
    DeleteSessionRequest,
    DeleteSessionResponse,
    SessionHistoryResponse,
    AllSessionsResponse,
    ChatMessageSchema,
    SessionSummary,
    CreateSessionResponse,
    ActiveSessionResponse,
    CollectionResponse,
    DocumentResponse,
    DeleteDocumentResponse,
    DeleteCollectionResponse,
    CollectionsListResponse,
    DocumentsListResponse
)

from app.services.ingest import ingest_pdf_file
from app.services.qa import answer_query
from app.services import status as job_status

from app.services.chat_memory import (
    delete_session_history,
    get_session_messages,
    get_all_sessions,
    create_new_session,
    get_active_session,
    deactivate_session
)

from app.db.database import get_db
from app.db.models import ChatSession, Collection, Document, Chunk, Embedding

import logging
import shutil
import os


router = APIRouter()
logger = logging.getLogger("app.api")


@router.post("/ingest", response_model=UploadResponse)
def ingest_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    collection: str = Query("default")
):
    """
    Upload a PDF and ingest it into pgvector database.
    Documents are shared across all sessions - no session_id required.
    
    Parameters:
    - file: PDF file to upload (form-data)
    - collection: Collection name (query parameter, default: "default")
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    upload_dir = os.path.join(os.getcwd(), "uploads")
    os.makedirs(upload_dir, exist_ok=True)

    tmp_path = os.path.join(upload_dir, file.filename)

    with open(tmp_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # generate a job id and record queued status
    import time
    job_id = f"{collection}-{file.filename}-{int(time.time())}"
    job_status.set_status(job_id, "queued")

    # Let FastAPI run the blocking ingestion in its thread pool via BackgroundTasks
    logger.info("Starting synchronous ingest for %s", file.filename)
    ingest_pdf_file(tmp_path, collection, job_id)

    return UploadResponse(
        filename=file.filename,
        collection=collection,
        status="completed",
        job_id=job_id
    )


@router.post("/query", response_model=QueryResponse)
def query_docs(payload: QueryRequest, db: Session = Depends(get_db)):
    """
    Retrieve from vector DB and generate an answer. Non-creative, faithful to sources.
    Supports chat memory when session_id is provided.
    """
    logger.info(
        "Query received for collection=%s, session_id=%s",
        payload.collection,
        payload.session_id
    )

    answer, source_docs = answer_query(
        payload.query,
        collection=payload.collection,
        k=payload.k,
        session_id=payload.session_id,
        db=db
    )

    return QueryResponse(
        answer=answer,
        sources=source_docs,
        session_id=payload.session_id
    )


# SESSION ENDPOINTS - Specific routes BEFORE parameterized routes
@router.post("/session/new", response_model=CreateSessionResponse)
def create_session(db: Session = Depends(get_db)):
    """
    Create a new chat session. This will deactivate any existing active session
    and create a new active session. Call this when user opens the chat widget.
    Returns the new session_id to use for subsequent queries.
    """
    logger.info("Create new session request")

    session = create_new_session(db)

    if not session:
        raise HTTPException(status_code=500, detail="Failed to create new session")

    return CreateSessionResponse(
        session_id=session.session_id,
        is_active=session.is_active,
        created_at=session.created_at,
        message="New session created successfully. Use this session_id for your queries."
    )


@router.get("/session/active", response_model=ActiveSessionResponse)
def get_current_active_session(db: Session = Depends(get_db)):
    """
    Get the currently active session with all its details and chat history.
    Returns the actual session_id from the database.
    Returns 404 if no active session exists.
    """
    logger.info("=== GET /session/active request START ===")

    session = get_active_session(db)

    logger.info(f"Session object retrieved: {session}")
    logger.info(f"Session type: {type(session)}")

    if not session:
        logger.error("No active session found in database")
        raise HTTPException(
            status_code=404,
            detail="No active session found. Create a new session using POST /api/session/new"
        )

    logger.info(f"Session ID from object: {session.session_id}")
    logger.info(f"Session is_active: {session.is_active}")
    logger.info(f"Session created_at: {session.created_at}")
    logger.info(f"Session last_activity: {session.last_activity}")

    messages = get_session_messages(db, session.session_id)
    logger.info(f"Messages count: {len(messages)}")

    response = ActiveSessionResponse(
        session_id=session.session_id,
        is_active=session.is_active,
        message_count=len(messages),
        created_at=session.created_at,
        last_activity=session.last_activity,
        messages=[
            ChatMessageSchema(
                role=msg.role,
                content=msg.content,
                created_at=msg.created_at
            )
            for msg in messages
        ]
    )

    logger.info(f"Response session_id: {response.session_id}")
    logger.info(f"Response object: {response}")
    logger.info(f"Response dict: {response.dict()}")
    logger.info("=== GET /session/active request END ===")

    return response


@router.get("/sessions", response_model=AllSessionsResponse)
def list_all_sessions(db: Session = Depends(get_db)):
    """
    Retrieve all sessions with their message counts and last activity.
    """
    logger.info("Get all sessions request")

    sessions = get_all_sessions(db)

    return AllSessionsResponse(
        total_sessions=len(sessions),
        sessions=[
            SessionSummary(
                session_id=s["session_id"],
                message_count=s["message_count"],
                is_active=s["is_active"],
                created_at=s["created_at"],
                last_activity=s["last_activity"]
            )
            for s in sessions
        ]
    )


# Parameterized routes AFTER specific routes
@router.get("/session/{session_id}", response_model=SessionHistoryResponse)
def get_session(session_id: UUID, db: Session = Depends(get_db)):
    """
    Retrieve all chat history for a specific session.
    """
    logger.info("Get session request for session_id=%s", session_id)

    messages = get_session_messages(db, session_id)

    return SessionHistoryResponse(
        session_id=session_id,
        message_count=len(messages),
        messages=[
            ChatMessageSchema(
                role=msg.role,
                content=msg.content,
                created_at=msg.created_at
            )
            for msg in messages
        ]
    )


@router.post("/session/{session_id}/deactivate")
def deactivate_chat_session(session_id: UUID, db: Session = Depends(get_db)):
    """
    Mark a session as inactive without deleting it.
    Use this when user minimizes/closes the chat but you want to keep history.
    """
    logger.info("Deactivate session request for session_id=%s", session_id)

    success = deactivate_session(db, session_id)

    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )

    return {
        "session_id": session_id,
        "is_active": False,
        "message": "Session deactivated successfully"
    }


@router.delete("/session/{session_id}", response_model=DeleteSessionResponse)
def delete_session(session_id: UUID, db: Session = Depends(get_db)):
    """
    Delete all chat history for a specific session.
    Call this when user closes the chat window.
    """
    logger.info("Delete session request for session_id=%s", session_id)

    deleted_count = delete_session_history(db, session_id)

    return DeleteSessionResponse(
        session_id=session_id,
        deleted_count=deleted_count,
        message=f"Successfully deleted {deleted_count} messages for session {session_id}"
    )


@router.get("/status/{job_id}")
def get_status(job_id: str):
    return {"job_id": job_id, "status": job_status.get_status(job_id)}


# ===== DOCUMENT & COLLECTION MANAGEMENT ENDPOINTS =====

@router.get("/collections", response_model=CollectionsListResponse)
def list_collections(db: Session = Depends(get_db)):
    """
    List all collections with their document counts.
    """
    collections = db.query(Collection).all()
    
    result = []
    for coll in collections:
        doc_count = db.query(Document).filter(Document.collection_id == coll.id).count()
        result.append(CollectionResponse(
            id=coll.id,
            name=coll.name,
            description=coll.description,
            created_at=coll.created_at,
            document_count=doc_count
        ))
    
    return CollectionsListResponse(
        total_collections=len(result),
        collections=result
    )


@router.get("/collections/{collection_name}/documents", response_model=DocumentsListResponse)
def get_documents_by_collection(collection_name: str, db: Session = Depends(get_db)):
    """
    Get all documents in a specific collection.
    """
    collection = db.query(Collection).filter(Collection.name == collection_name).first()
    
    if not collection:
        raise HTTPException(status_code=404, detail=f"Collection '{collection_name}' not found")
    
    documents = db.query(Document).filter(Document.collection_id == collection.id).all()
    
    result = []
    for doc in documents:
        chunk_count = db.query(Chunk).filter(Chunk.document_id == doc.id).count()
        result.append(DocumentResponse(
            id=doc.id,
            collection_name=collection.name,
            filename=doc.filename,
            document_type=doc.document_type,
            title=doc.title,
            created_at=doc.created_at,
            chunk_count=chunk_count
        ))
    
    return DocumentsListResponse(
        collection_name=collection_name,
        total_documents=len(result),
        documents=result
    )


@router.get("/documents/{document_id}", response_model=DocumentResponse)
def get_document_by_id(document_id: UUID, db: Session = Depends(get_db)):
    """
    Get a specific document by its ID, including collection info.
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
    
    chunk_count = db.query(Chunk).filter(Chunk.document_id == document.id).count()
    
    return DocumentResponse(
        id=document.id,
        collection_name=document.collection.name,
        filename=document.filename,
        document_type=document.document_type,
        title=document.title,
        created_at=document.created_at,
        chunk_count=chunk_count
    )


@router.delete("/documents/{document_id}", response_model=DeleteDocumentResponse)
def delete_document_by_id(document_id: UUID, db: Session = Depends(get_db)):
    """
    Delete a document by its ID.
    This will CASCADE delete all associated chunks and embeddings.
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
    
    # Count what will be deleted
    chunk_count = db.query(Chunk).filter(Chunk.document_id == document.id).count()
    embedding_count = db.query(Embedding).filter(Embedding.document_id == document.id).count()
    
    filename = document.filename
    collection_name = document.collection.name
    
    # Delete document (CASCADE will handle chunks and embeddings)
    db.delete(document)
    db.commit()
    
    logger.info(f"Deleted document {document_id} ({filename}) with {chunk_count} chunks and {embedding_count} embeddings")
    
    return DeleteDocumentResponse(
        document_id=document_id,
        filename=filename,
        collection_name=collection_name,
        chunks_deleted=chunk_count,
        embeddings_deleted=embedding_count,
        message=f"Successfully deleted document '{filename}' and all associated data"
    )


@router.delete("/collections/{collection_name}/documents", response_model=DeleteCollectionResponse)
def delete_all_documents_in_collection(collection_name: str, db: Session = Depends(get_db)):
    """
    Delete all documents in a specific collection.
    This will CASCADE delete all associated chunks and embeddings.
    The collection itself is also deleted.
    """
    collection = db.query(Collection).filter(Collection.name == collection_name).first()
    
    if not collection:
        raise HTTPException(status_code=404, detail=f"Collection '{collection_name}' not found")
    
    # Count what will be deleted
    documents = db.query(Document).filter(Document.collection_id == collection.id).all()
    doc_count = len(documents)
    
    total_chunks = 0
    total_embeddings = 0
    for doc in documents:
        total_chunks += db.query(Chunk).filter(Chunk.document_id == doc.id).count()
        total_embeddings += db.query(Embedding).filter(Embedding.document_id == doc.id).count()
    
    # Delete collection (CASCADE will handle documents, chunks, and embeddings)
    db.delete(collection)
    db.commit()
    
    logger.info(
        f"Deleted collection '{collection_name}' with {doc_count} documents, "
        f"{total_chunks} chunks, and {total_embeddings} embeddings"
    )
    
    return DeleteCollectionResponse(
        collection_name=collection_name,
        documents_deleted=doc_count,
        chunks_deleted=total_chunks,
        embeddings_deleted=total_embeddings,
        message=f"Successfully deleted collection '{collection_name}' and all {doc_count} documents with associated data"
    )


# python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

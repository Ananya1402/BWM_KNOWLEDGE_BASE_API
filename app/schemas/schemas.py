from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from uuid import UUID


class UploadResponse(BaseModel):
    filename: str
    collection: str
    status: str
    job_id: Optional[str] = None


class QueryRequest(BaseModel):
    query: str
    collection: str = "default"
    k: int = 4
    session_id: Optional[UUID] = None  # Optional session ID for chat memory


class QueryResponse(BaseModel):
    answer: str
    sources: List[str]
    session_id: Optional[UUID] = None  # Return session_id if provided


class DeleteSessionRequest(BaseModel):
    session_id: str


class DeleteSessionResponse(BaseModel):
    session_id: UUID
    deleted_count: int
    message: str


class ChatMessageSchema(BaseModel):
    role: str
    content: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SessionHistoryResponse(BaseModel):
    session_id: UUID
    message_count: int
    messages: List[ChatMessageSchema]


class SessionSummary(BaseModel):
    session_id: UUID
    message_count: int
    is_active: bool = True
    created_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None


class AllSessionsResponse(BaseModel):
    total_sessions: int
    sessions: List[SessionSummary]


class CreateSessionResponse(BaseModel):
    session_id: UUID
    is_active: bool
    created_at: datetime
    message: str


class ActiveSessionResponse(BaseModel):
    session_id: UUID  # The actual session ID from database
    is_active: bool
    message_count: int
    created_at: datetime
    last_activity: datetime
    messages: List[ChatMessageSchema]

    class Config:
        from_attributes = True

# Document and Collection Schemas
class CollectionResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    created_at: datetime
    document_count: int = 0

    class Config:
        from_attributes = True


class DocumentResponse(BaseModel):
    id: UUID
    collection_name: str
    filename: str
    document_type: str
    title: Optional[str] = None
    created_at: datetime
    chunk_count: int = 0

    class Config:
        from_attributes = True


class DeleteDocumentResponse(BaseModel):
    document_id: UUID
    filename: str
    collection_name: str
    chunks_deleted: int
    embeddings_deleted: int
    message: str


class DeleteCollectionResponse(BaseModel):
    collection_name: str
    documents_deleted: int
    chunks_deleted: int
    embeddings_deleted: int
    message: str


class CollectionsListResponse(BaseModel):
    total_collections: int
    collections: List[CollectionResponse]


class DocumentsListResponse(BaseModel):
    collection_name: str
    total_documents: int
    documents: List[DocumentResponse]
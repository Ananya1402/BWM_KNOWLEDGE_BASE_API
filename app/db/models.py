from sqlalchemy import Column, String, Text, DateTime, Boolean, ForeignKey, Integer, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.db.database import Base
from pgvector.sqlalchemy import Vector


class ChatSession(Base):
    """Model to track chat sessions"""
    __tablename__ = "chat_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        unique=True,
        nullable=False,
        index=True,
        default=uuid.uuid4
    )
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_activity = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    # Relationship to messages
    messages = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<ChatSession(session_id={self.session_id}, is_active={self.is_active})>"


class ChatMessage(Base):
    """Model to store chat messages for session memory"""
    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("chat_sessions.session_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship to session
    session = relationship("ChatSession", back_populates="messages")

    def __repr__(self):
        return f"<ChatMessage(session_id={self.session_id}, role={self.role})>"


class Collection(Base):
    """Model to organize documents into collections"""
    __tablename__ = "collections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    documents = relationship("Document", back_populates="collection", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Collection(name={self.name})>"


class Document(Base):
    """Model to store uploaded documents metadata - organized by collection"""
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    collection_id = Column(
        UUID(as_uuid=True),
        ForeignKey("collections.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    filename = Column(String(255), nullable=False)
    document_type = Column(String(50), default="pdf")  # pdf, webpage, etc.
    source_url = Column(String(500), nullable=True)
    title = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    collection = relationship("Collection", back_populates="documents")
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Document(id={self.id}, filename={self.filename}, collection={self.collection.name if self.collection else 'None'})>"


class Chunk(Base):
    """Model to store text chunks from documents"""
    __tablename__ = "chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    document = relationship("Document", back_populates="chunks")
    embeddings = relationship("Embedding", back_populates="chunk", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Chunk(id={self.id}, chunk_index={self.chunk_index})>"


class Embedding(Base):
    """Model to store vector embeddings for chunks using pgvector"""
    __tablename__ = "embeddings"
    
    # Note: The vector similarity index will be created manually in Alembic migration
    # because SQLAlchemy doesn't fully support pgvector index syntax

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chunk_id = Column(
        UUID(as_uuid=True),
        ForeignKey("chunks.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    # Vector column for pgvector (1536 dimensions for text-embedding-3-small)
    embedding = Column(Vector(1536), nullable=False)
    embedding_model = Column(String(100), default="text-embedding-3-small")
    text_preview = Column(Text, nullable=True)  # First 200 chars for reference
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    chunk = relationship("Chunk", back_populates="embeddings")

    def __repr__(self):
        return f"<Embedding(id={self.id}, chunk_id={self.chunk_id})>"


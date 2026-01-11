from sqlalchemy import Column, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.db.database import Base


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


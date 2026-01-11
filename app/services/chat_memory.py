# services/chat_memory.py
import logging
import uuid
from typing import List, Dict, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct
from app.db.models import ChatMessage, ChatSession

logger = logging.getLogger("app.chat_memory")


def get_chat_history(db: Session, session_id: UUID, limit: int = 10) -> List[Dict[str, str]]:
    """
    Retrieve chat history for a session.
    Returns list of messages in chronological order.
    """
    try:
        messages = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
            .limit(limit * 2)
            .all()
        )  # *2 for user+assistant pairs

        return [{"role": msg.role, "content": msg.content} for msg in messages]
    except Exception as e:
        logger.error(f"Failed to get chat history: {e}")
        return []


def save_message(db: Session, session_id: UUID, role: str, content: str) -> bool:
    """
    Save a single message to the chat history.
    """
    try:
        message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content
        )
        db.add(message)
        db.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to save message: {e}")
        db.rollback()
        return False


def save_conversation_turn(db: Session, session_id: UUID, user_query: str, assistant_response: str) -> bool:
    """
    Save both user query and assistant response as a conversation turn.
    Also updates the session's last_activity timestamp.
    """
    try:
        user_msg = ChatMessage(session_id=session_id, role="user", content=user_query)
        assistant_msg = ChatMessage(session_id=session_id, role="assistant", content=assistant_response)

        db.add(user_msg)
        db.add(assistant_msg)

        session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
        if session:
            session.last_activity = func.now()

        db.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to save conversation turn: {e}")
        db.rollback()
        return False


def delete_session_history(db: Session, session_id: UUID) -> int:
    """
    Delete all chat history and the session record.
    Returns number of deleted messages.
    """
    try:
        deleted_count = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .delete()
        )

        db.query(ChatSession).filter(
            ChatSession.session_id == session_id
        ).delete()

        db.commit()
        logger.info(f"Deleted {deleted_count} messages and session {session_id}")
        return deleted_count
    except Exception as e:
        logger.error(f"Failed to delete session history: {e}")
        db.rollback()
        return 0


def format_chat_history_for_prompt(chat_history: List[Dict[str, str]]) -> str:
    """
    Format chat history into a string for inclusion in the prompt.
    """
    if not chat_history:
        return ""

    formatted = "Previous conversation:\n"
    for msg in chat_history:
        role_label = "User" if msg["role"] == "user" else "Assistant"
        formatted += f"{role_label}: {msg['content']}\n"

    return formatted


def get_session_messages(db: Session, session_id: UUID) -> List[ChatMessage]:
    """
    Get all messages for a specific session with full details.
    """
    try:
        return (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
            .all()
        )
    except Exception as e:
        logger.error(f"Failed to get session messages: {e}")
        return []


def get_all_sessions(db: Session) -> List[Dict]:
    """
    Get all sessions with their message counts and activity info.
    """
    try:
        sessions = db.query(ChatSession).all()
        result = []

        for session in sessions:
            message_count = (
                db.query(func.count(ChatMessage.id))
                .filter(ChatMessage.session_id == session.session_id)
                .scalar()
            )

            result.append({
                "session_id": session.session_id,
                "message_count": message_count,
                "is_active": session.is_active,
                "created_at": session.created_at,
                "last_activity": session.last_activity
            })

        return result
    except Exception as e:
        logger.error(f"Failed to get all sessions: {e}")
        return []


def create_new_session(db: Session) -> Optional[ChatSession]:
    """
    Create a new chat session. Deactivates any existing active sessions first.
    Returns the new session.
    """
    try:
        db.query(ChatSession).filter(
            ChatSession.is_active == True
        ).update({"is_active": False})

        session_id = uuid.uuid4()

        new_session = ChatSession(
            session_id=session_id,
            is_active=True
        )

        db.add(new_session)
        db.commit()
        db.refresh(new_session)

        logger.info(f"Created new session: {session_id}")
        return new_session
    except Exception as e:
        logger.error(f"Failed to create new session: {e}")
        db.rollback()
        return None


def get_active_session(db: Session) -> Optional[ChatSession]:
    """
    Get the currently active session.
    Returns None if no active session exists.
    """
    try:
        logger.info("=== get_active_session() START ===")

        session = (
            db.query(ChatSession)
            .filter(ChatSession.is_active == True)
            .order_by(ChatSession.last_activity.desc())
            .first()
        )

        if session:
            logger.info(f"Found active session: {session.session_id}")
            logger.info(
                f"Session attributes - id: {session.id}, session_id: {session.session_id}, "
                f"is_active: {session.is_active}"
            )
        else:
            logger.warning("No active session found in database")

        logger.info("=== get_active_session() END ===")
        return session
    except Exception as e:
        logger.error(f"Failed to get active session: {e}", exc_info=True)
        return None


def deactivate_session(db: Session, session_id: UUID) -> bool:
    """
    Mark a session as inactive (without deleting it).
    """
    try:
        session = db.query(ChatSession).filter(
            ChatSession.session_id == session_id
        ).first()

        if session:
            session.is_active = False
            db.commit()
            logger.info(f"Deactivated session: {session_id}")
            return True

        return False
    except Exception as e:
        logger.error(f"Failed to deactivate session: {e}")
        db.rollback()
        return False
        return []

# services/qa.py
import logging
from typing import List, Tuple, Optional, Dict
from uuid import UUID
from sqlalchemy.orm import Session
from app.core import config
from app.services.pg_vector_client import get_embedding, get_openai_client, similarity_search
from app.services.chat_memory import (
    get_chat_history,
    save_conversation_turn,
    format_chat_history_for_prompt
)

logger = logging.getLogger("app.qa")

SYSTEM_PROMPT = """You are a helpful Q&A assistant for a knowledge base. Your role is to answer questions based on the provided context from documents.

Guidelines:
1. Answer questions based ONLY on the provided document context.
2. If there is previous conversation history, use it to understand follow-up questions and maintain context.
3. If the answer is not in the provided context, say you don't know.
4. Be concise but thorough in your responses.
5. When referencing information, be clear about what you're basing your answer on."""


def answer_query(
    query: str,
    collection: str = "default",
    k: int = 4,
    session_id: Optional[UUID] = None,
    db: Optional[Session] = None
) -> Tuple[str, List[str]]:
    """
    Answer query using pgvector similarity search.
    """
    try:
        # ===== PGVECTOR QUERY =====
        query_embedding = get_embedding(query)
        
        # Perform similarity search using pgvector (searches ALL documents)
        docs, sources = similarity_search(
            db=db,
            query_embedding=query_embedding,
            k=k
        )
        # ===== END PGVECTOR =====

        context = "\n\n".join(docs)

        if not context:
            return "I couldn't find any relevant information in the documents.", []

        chat_history = []
        chat_history_text = ""

        if session_id and db:
            chat_history = get_chat_history(db, session_id, limit=10)
            chat_history_text = format_chat_history_for_prompt(chat_history)

        if chat_history_text:
            prompt = (
                f"{chat_history_text}\n\nDocument Context:\n{context}"
                f"\n\nCurrent Question: {query}"
            )
        else:
            prompt = f"Document Context:\n{context}\n\nQuestion: {query}"

        client = get_openai_client()

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1024
        )

        answer = response.choices[0].message.content

        if session_id and db:
            save_conversation_turn(db, session_id, query, answer)

        return answer, list(set(sources))

    except Exception as e:
        logger.error("Query failed: %s", e, exc_info=True)
        return "I encountered an error processing your search.", []

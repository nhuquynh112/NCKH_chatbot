from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone
from app.models import ChatSession, ChatMessage
from app.schemas.chat import ChatSessionCreate

def utc_now():
    return datetime.now(timezone.utc)

class ChatRepository:
    def __init__(self, db: Session):
        self.db = db

    # --- Session Methods ---
    def get_session(self, session_id: UUID) -> Optional[ChatSession]:
        return self.db.query(ChatSession).filter(ChatSession.id == session_id).first()

    def create_session(self, session_in: ChatSessionCreate) -> ChatSession:
        db_session = ChatSession(**session_in.model_dump())
        self.db.add(db_session)
        self.db.commit()
        self.db.refresh(db_session)
        return db_session

    def close_session(self, session_id: UUID) -> Optional[ChatSession]:
        session = self.get_session(session_id)
        if session and session.status != "closed":
            session.status = "closed"
            session.ended_at = utc_now()
            self.db.commit()
            self.db.refresh(session)
        return session

    # --- Message Methods ---
    def create_message(
        self,
        session_id: UUID,
        role: str,
        content: str,
        confidence: Optional[float] = None,
        response_time_ms: Optional[int] = None,
        sources: list = None,
        intent: Optional[str] = None
    ) -> ChatMessage:
        if sources is None:
            sources = []
            
        db_message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            confidence=confidence,
            response_time_ms=response_time_ms,
            sources=sources,
            intent=intent
        )
        self.db.add(db_message)
        self.db.commit()
        self.db.refresh(db_message)
        return db_message

    def get_messages_by_session(self, session_id: UUID, skip: int = 0, limit: int = 50) -> List[ChatMessage]:
        return self.db.query(ChatMessage)\
            .filter(ChatMessage.session_id == session_id)\
            .order_by(ChatMessage.created_at.asc())\
            .offset(skip).limit(limit).all()

    def get_recent_messages(
        self,
        session_id: UUID,
        limit: int = 6,
    ) -> List[ChatMessage]:
        """
        Lấy N tin nhắn gần nhất của một phiên chat.
        Kết quả được trả về theo đúng thứ tự thời gian (cũ -> mới)
        để đưa vào prompt cho LLM.
        """

        messages = (
            self.db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
            .all()
        )

        return list(reversed(messages))
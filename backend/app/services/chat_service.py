import time
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.repositories.chat_repository import ChatRepository
from app.repositories.ticket_repository import TicketRepository
from app.services.ai_service import AIService
from app.schemas.chat import ChatSessionCreate, ChatMessageRequest
from app.schemas.ticket import TicketCreate
from app.models import ChatSession, ChatMessage

class ChatService:
    def __init__(self, db: Session):
        self.chat_repo = ChatRepository(db)
        self.ticket_repo = TicketRepository(db)
        self.ai_service = AIService()

    def create_session(self, session_in: ChatSessionCreate) -> ChatSession:
        return self.chat_repo.create_session(session_in)

    def close_session(self, session_id: UUID) -> ChatSession:
        session = self.chat_repo.close_session(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chat session {session_id} not found."
            )
        return session
        
    def get_session_messages(self, session_id: UUID, skip: int = 0, limit: int = 50):
        # Verify session exists
        session = self.chat_repo.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chat session {session_id} not found."
            )
        return self.chat_repo.get_messages_by_session(session_id, skip=skip, limit=limit)

    async def process_message(self, request: ChatMessageRequest):
        # 1. Verify session
        session = self.chat_repo.get_session(request.session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chat session {request.session_id} not found."
            )

        if session.status == "closed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot send message to a closed session."
            )

        # 2. Save User Message
        self.chat_repo.create_message(
            session_id=session.id,
            role="user",
            content=request.content
        )

        # 2.1 Load recent conversation history
        recent_messages = self.chat_repo.get_recent_messages(
            session_id=session.id,
            limit=6
        )
        history = [
            {
                "role": msg.role,
                "content": msg.content
            }
            for msg in recent_messages
        ]

        # 3. Call AI Service (measure time)
        start_time = time.time()
        ai_response = await self.ai_service.query(
            session_id=str(session.id),
            message=request.content,
            history=history,
            product_id=request.product_id
        )
        end_time = time.time()
        response_time_ms = int((end_time - start_time) * 1000)

        # 4. Save Assistant Message
        assistant_message = self.chat_repo.create_message(
            session_id=session.id,
            role="assistant",
            content=ai_response.answer,
            confidence=ai_response.confidence,
            response_time_ms=response_time_ms,
            sources=ai_response.sources,
            intent=ai_response.intent
        )

        ticket_created = False
        
        # 5. Create ticket if needed
        if ai_response.needs_human or (ai_response.confidence and ai_response.confidence < 0.5):
            ticket_in = TicketCreate(
                session_id=session.id,
                trigger_message_id=assistant_message.id,
                subject=f"Hỗ trợ khách hàng: Cần nhân viên hỗ trợ ({session.customer_name or session.visitor_id})",
                issue=f"Tin nhắn cuối của khách: '{request.content}'. AI Response: '{ai_response.answer}'",
                customer_name=session.customer_name,
                customer_email=session.customer_email,
                priority="high"
            )
            self.ticket_repo.create(ticket_in)
            ticket_created = True

        return assistant_message, ticket_created

def get_chat_service(db: Session) -> ChatService:
    return ChatService(db)

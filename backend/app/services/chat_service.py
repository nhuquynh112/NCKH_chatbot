import time
import re
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.repositories.chat_repository import ChatRepository
from app.repositories.faq_repository import FAQRepository
from app.repositories.ticket_repository import TicketRepository
from app.services.ai_service import AIQueryResponse, AIService
from app.schemas.chat import ChatSessionCreate, ChatMessageRequest
from app.schemas.ticket import TicketCreate
from app.models import ChatSession, ChatMessage
from app.rag.query_rewriter import strip_accents

class ChatService:
    def __init__(self, db: Session):
        self.chat_repo = ChatRepository(db)
        self.ticket_repo = TicketRepository(db)
        self.faq_repo = FAQRepository(db)
        # Initializing the RAG index can be expensive on the first run.  Do it
        # only when a message needs AI, not when creating/loading a session.
        self._ai_service = None

    @property
    def ai_service(self) -> AIService:
        if self._ai_service is None:
            self._ai_service = AIService()
        return self._ai_service

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

    def get_sessions_by_visitor(self, visitor_id: str, limit: int = 50):
        return self.chat_repo.get_sessions_by_visitor(visitor_id, limit=limit)

    def assert_session_owner(self, session_id: UUID, visitor_id: str):
        session = self.chat_repo.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        if session.visitor_id != visitor_id:
            # Do not reveal whether another visitor's session exists.
            raise HTTPException(status_code=404, detail="Session not found")
        return session

    def update_session_title(self, session_id: UUID, title: str):
        session = self.chat_repo.update_session_title(session_id, title.strip()[:255])
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return session

    def delete_session(self, session_id: UUID):
        if not self.chat_repo.delete_session(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        return True

    async def generate_and_update_title(self, session_id: UUID, message: str) -> str:
        if not self.chat_repo.get_session(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        title = await self.ai_service.generate_title(message)
        self.chat_repo.update_session_title(session_id, title)
        return title

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

        phone_number = self._extract_phone_number(request.content)
        sensitive_kind = self._sensitive_data_kind(request.content)
        stored_content = self._redact_for_storage(request.content)

        # 2. Save a privacy-safe copy of the user message. Contact phone
        # numbers remain available in the dedicated ticket field when needed,
        # but chat history never needs to expose them in full.
        self.chat_repo.create_message(
            session_id=session.id,
            role="user",
            content=stored_content,
        )

        open_ticket = self.ticket_repo.get_open_by_session(session.id)

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

        if sensitive_kind:
            assistant_message = self.chat_repo.create_message(
                session_id=session.id,
                role="assistant",
                content=(
                    f"Mình đã ẩn {sensitive_kind} khỏi lịch sử hiển thị để bảo vệ bạn. "
                    "TechCare không bao giờ cần mật khẩu, mã OTP, mã CVV/CVC hoặc toàn bộ số thẻ qua chat. "
                    "Nếu thông tin này còn hiệu lực, bạn nên đổi mật khẩu hoặc liên hệ ngân hàng ngay."
                ),
                confidence=1.0,
                response_time_ms=0,
                sources=[],
                intent="sensitive_data_warning",
            )
            return assistant_message, False

        # Contact details are a reply to the current support flow, not a new
        # product question. Persist them before asking the LLM so a phone
        # number can never be misread as a model or category query.
        if phone_number and (
            open_ticket or self._history_requests_contact(recent_messages)
        ):
            if open_ticket is None:
                previous_context = " | ".join(
                    msg.content
                    for msg in recent_messages[:-1]
                    if msg.role == "user"
                )
                open_ticket = self.ticket_repo.create(
                    TicketCreate(
                        session_id=session.id,
                        subject=(
                            "Hỗ trợ khách hàng: Khách đã cung cấp thông tin liên hệ "
                            f"({session.customer_name or session.visitor_id})"
                        ),
                        issue=f"Nội dung khách đã trao đổi: '{previous_context}'.",
                        customer_name=session.customer_name,
                        customer_email=session.customer_email,
                        customer_phone=phone_number,
                        priority="high",
                    )
                )
                ticket_created = True
            else:
                self.ticket_repo.update_customer_phone(open_ticket, phone_number)
                ticket_created = False

            masked_phone = self._mask_phone(phone_number)
            assistant_message = self.chat_repo.create_message(
                session_id=session.id,
                role="assistant",
                content=(
                    f"Mình đã lưu số điện thoại {masked_phone} vào ticket #{open_ticket.id}. "
                    "Nhân viên TechCare sẽ dùng số này để liên hệ về đúng yêu cầu đang trao đổi. "
                    "Bạn không cần và không nên gửi mật khẩu, mã OTP hoặc thông tin thẻ."
                ),
                confidence=1.0,
                response_time_ms=0,
                sources=[],
                intent="ticket_contact_received",
            )
            return assistant_message, ticket_created

        if open_ticket:
            self.ticket_repo.append_customer_message(open_ticket, request.content)

        # 3. Call AI Service (measure time). An exact admin FAQ is already a
        # trusted final answer, so it does not need a slower LLM round-trip.
        start_time = time.time()
        faq_documents = self._relevant_faq_documents(request.content)
        exact_faq = next((item for item in faq_documents if item.get("exact")), None)
        if exact_faq:
            ai_response = AIQueryResponse(
                answer=exact_faq["answer"],
                confidence=1.0,
                intent="faq",
                sources=[
                    {
                        "id": exact_faq["id"],
                        "title": exact_faq["title"],
                        "score": 1.0,
                        "metadata": exact_faq["metadata"],
                    }
                ],
                needs_human=False,
            )
        else:
            ai_response = await self.ai_service.query(
                session_id=str(session.id),
                message=request.content,
                history=history,
                product_id=request.product_id,
                faq_documents=faq_documents,
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
        if (ai_response.needs_human or ai_response.confidence < 0.5) and not open_ticket:
            user_context = " | ".join(
                message["content"]
                for message in history
                if message["role"] == "user"
            )
            ticket_in = TicketCreate(
                session_id=session.id,
                trigger_message_id=assistant_message.id,
                subject=f"Hỗ trợ khách hàng: Cần nhân viên hỗ trợ ({session.customer_name or session.visitor_id})",
                issue=f"Nội dung khách đã trao đổi: '{user_context}'. AI Response: '{ai_response.answer}'",
                customer_name=session.customer_name,
                customer_email=session.customer_email,
                priority="high"
            )
            self.ticket_repo.create(ticket_in)
            ticket_created = True

        return assistant_message, ticket_created

    @staticmethod
    def _extract_phone_number(text: str) -> str | None:
        match = re.search(
            r"(?<!\d)(?:\+?84|0)(?:[\s.\-]*\d){9}(?!\d)",
            text,
        )
        if not match:
            return None
        digits = re.sub(r"\D", "", match.group(0))
        if digits.startswith("84"):
            digits = "0" + digits[2:]
        if re.fullmatch(r"0[35789]\d{8}", digits):
            return digits
        return None

    @staticmethod
    def _mask_phone(phone: str) -> str:
        return f"{phone[:4]}***{phone[-3:]}"

    @staticmethod
    def _sensitive_data_kind(text: str) -> str | None:
        folded = strip_accents(text.lower())
        if re.search(r"\b(?:otp|ma otp)\b.{0,30}\b\d{4,8}\b|\b\d{4,8}\b.{0,30}\b(?:otp|ma otp)\b", folded):
            return "mã OTP"
        if re.search(r"\b(?:mat khau|password|passwd)\b\s*(?:la|:|=)?\s*\S+", folded):
            return "mật khẩu"
        if re.search(r"\b(?:cvv|cvc)\b.{0,20}\b\d{3,4}\b", folded):
            return "mã bảo mật thẻ"
        card_candidates = re.findall(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)", text)
        if any(13 <= len(re.sub(r"\D", "", candidate)) <= 19 for candidate in card_candidates):
            return "số thẻ thanh toán"
        return None

    @classmethod
    def _redact_for_storage(cls, text: str) -> str:
        safe = text
        phone = cls._extract_phone_number(safe)
        if phone:
            raw_phone = re.search(r"(?<!\d)(?:\+?84|0)(?:[\s.\-]*\d){9}(?!\d)", safe)
            if raw_phone:
                safe = safe[:raw_phone.start()] + cls._mask_phone(phone) + safe[raw_phone.end():]
        safe = re.sub(
            r"(?i)(\b(?:otp|mã otp|ma otp)\b[^\d\r\n]{0,40})\d{4,8}\b",
            r"\1[ĐÃ ẨN]",
            safe,
        )
        safe = re.sub(
            r"(?i)\b(?:mật khẩu|mat khau|password|passwd)\b\s*(?:là|la|:|=)?\s*\S+",
            "[MẬT KHẨU ĐÃ ẨN]",
            safe,
        )
        safe = re.sub(
            r"(?i)\b(?:cvv|cvc)\b\s*(?:là|la|:|=)?\s*\d{3,4}\b",
            "[MÃ BẢO MẬT THẺ ĐÃ ẨN]",
            safe,
        )
        safe = re.sub(
            r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)",
            "[SỐ THẺ ĐÃ ẨN]",
            safe,
        )
        return safe

    @staticmethod
    def _history_requests_contact(messages: list[ChatMessage]) -> bool:
        for message in reversed(messages[:-1]):
            if message.role != "assistant":
                continue
            folded = strip_accents(message.content.lower())
            return (
                "so dien thoai" in folded
                and any(term in folded for term in ["ticket", "nhan vien", "lien he"])
            )
        return False

    def _relevant_faq_documents(self, question: str) -> list[dict]:
        folded_question = strip_accents(question.lower())
        question_tokens = self._meaningful_tokens(folded_question)
        if not question_tokens:
            return []

        ranked: list[tuple[float, object, bool]] = []
        for faq in self.faq_repo.get_active():
            folded_faq_question = strip_accents(faq.question.lower())
            faq_text = strip_accents(
                f"{faq.question} {faq.answer} {' '.join(faq.keywords or [])}".lower()
            )
            faq_tokens = self._meaningful_tokens(faq_text)
            overlap = len(question_tokens & faq_tokens) / len(question_tokens)
            exact = folded_question.strip(" ?!.") == folded_faq_question.strip(" ?!.")
            if exact:
                overlap = 1.0
            if overlap >= 0.60:
                ranked.append((overlap, faq, exact))

        ranked.sort(key=lambda item: item[0], reverse=True)
        return [
            {
                "id": f"faq-{faq.id}",
                "title": faq.question,
                "content": f"FAQ do quản trị viên cập nhật:\nCâu hỏi: {faq.question}\nCâu trả lời: {faq.answer}",
                "answer": faq.answer,
                "exact": exact,
                # Admin-managed FAQs are curated first-party answers and take
                # precedence over semantically related knowledge-base chunks.
                "score": 2.0 + min(1.0, score),
                "metadata": {"source": "faq_database", "category": faq.category},
            }
            for score, faq, exact in ranked[:2]
        ]

    @staticmethod
    def _meaningful_tokens(text: str) -> set[str]:
        stop_words = {"co", "khong", "la", "gi", "nao", "the", "toi", "minh", "ban", "shop", "cua", "ve"}
        return {
            token
            for token in re.findall(r"[a-z0-9]+", text)
            if len(token) >= 2 and token not in stop_words
        }

def get_chat_service(db: Session) -> ChatService:
    return ChatService(db)

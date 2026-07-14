import asyncio
import logging
import threading
from typing import Optional

from pydantic import BaseModel, Field

from app.config import settings
from app.rag.chat_service import ChatResult, create_default_chat_service
from app.rag.chroma_store import ChromaUnavailableError
from app.rag.embedding import OllamaError


logger = logging.getLogger(__name__)


class AIQueryRequest(BaseModel):
    session_id: str
    message: str
    product_id: Optional[int] = None


class AIQueryResponse(BaseModel):
    answer: str
    confidence: float
    intent: Optional[str] = None
    sources: list = Field(default_factory=list)
    needs_human: bool = False


class AIService:
    _chatbot = None
    _chatbot_lock = threading.Lock()

    def __init__(self):
        self.startup_error: Exception | None = None
        try:
            self.chatbot = self._get_or_create_chatbot()
        except (OllamaError, ChromaUnavailableError, ValueError, RuntimeError) as exc:
            logger.error("Local RAG chatbot initialization failed: %s", exc)
            self.chatbot = None
            self.startup_error = exc

    @classmethod
    def _get_or_create_chatbot(cls):
        if cls._chatbot is not None:
            return cls._chatbot

        with cls._chatbot_lock:
            if cls._chatbot is None:
                logger.info("Initializing local RAG chatbot")
                cls._chatbot = create_default_chat_service(
                    config=settings,
                    ensure_index=True,
                )
        return cls._chatbot

    async def query(
        self,
        session_id: str,
        message: str,
        product_id: Optional[int] = None,
    ) -> AIQueryResponse:
        request_data = AIQueryRequest(
            session_id=str(session_id),
            message=message,
            product_id=product_id,
        )

        if self.chatbot is None:
            if self.startup_error is not None:
                logger.error("Local AI service is unavailable: %s", self.startup_error)
            return self._service_unavailable_response()

        try:
            result = await asyncio.to_thread(
                self.chatbot.ask,
                request_data.message,
                settings.RAG_TOP_K,
            )
            return self._to_ai_response(result)
        except (OllamaError, ChromaUnavailableError, ValueError) as exc:
            logger.error("Local AI service failed: %s", exc)
            return self._service_unavailable_response()
        except RuntimeError as exc:
            logger.exception("Unexpected local AI runtime error")
            return self._service_unavailable_response()

    def _to_ai_response(self, result: ChatResult) -> AIQueryResponse:
        return AIQueryResponse(
            answer=result.answer,
            confidence=self._confidence_from_result(result),
            intent=result.mode,
            sources=self._sources_from_result(result),
            needs_human=result.needs_human,
        )

    def _confidence_from_result(self, result: ChatResult) -> float:
        if result.mode == "fallback":
            return 0.0
        if result.sources:
            return max(0.0, min(1.0, result.sources[0].score))
        if result.mode == "rule+rag":
            return 0.95
        return 0.7

    def _sources_from_result(self, result: ChatResult) -> list[dict]:
        sources = []
        for hit in result.sources:
            sources.append(
                {
                    "id": hit.document.id,
                    "title": hit.document.title,
                    "score": round(hit.score, 4),
                    "metadata": hit.document.metadata,
                }
            )
        return sources

    def _service_unavailable_response(self) -> AIQueryResponse:
        return AIQueryResponse(
            answer=(
                "Xin lỗi, hệ thống AI đang gặp sự cố. "
                "Mình sẽ tạo ticket để nhân viên hỗ trợ kiểm tra và phản hồi cho bạn."
            ),
            confidence=0.0,
            intent="ai_unavailable",
            needs_human=True,
        )

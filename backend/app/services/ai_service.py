import httpx
from typing import Dict, Any, Optional
from pydantic import BaseModel
from app.config import settings

class AIQueryRequest(BaseModel):
    session_id: str
    message: str
    product_id: Optional[int] = None

class AIQueryResponse(BaseModel):
    answer: str
    confidence: float
    intent: Optional[str] = None
    sources: list = []
    needs_human: bool = False

class AIService:
    def __init__(self):
        self.ai_url = settings.AI_SERVICE_URL

    async def query(self, session_id: str, message: str, product_id: Optional[int] = None) -> AIQueryResponse:
        request_data = AIQueryRequest(
            session_id=str(session_id),
            message=message,
            product_id=product_id
        )

        if not self.ai_url:
            # Mock response if no AI_SERVICE_URL is provided
            return self._mock_query(request_data)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.ai_url.rstrip('/')}/query",
                    json=request_data.model_dump(),
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                return AIQueryResponse(**data)
            except Exception as e:
                print(f"Error calling AI Service: {e}")
                # Fallback to mock or raise exception? Usually fallback or raise. We'll return a graceful failure mock.
                return AIQueryResponse(
                    answer="Xin lỗi, hệ thống AI đang gặp sự cố. Vui lòng thử lại sau.",
                    confidence=0.0,
                    needs_human=True
                )

    def _mock_query(self, request_data: AIQueryRequest) -> AIQueryResponse:
        # Simple mock logic based on keywords
        msg = request_data.message.lower()
        if "giá" in msg or "price" in msg:
            return AIQueryResponse(
                answer="Giá của sản phẩm này là 1.000.000đ.",
                confidence=0.9,
                intent="price_inquiry"
            )
        elif "lỗi" in msg or "error" in msg:
            return AIQueryResponse(
                answer="Có vẻ bạn đang gặp sự cố kỹ thuật. Tôi sẽ chuyển bạn đến nhân viên hỗ trợ.",
                confidence=0.4,
                intent="technical_support",
                needs_human=True
            )
        
        return AIQueryResponse(
            answer="Cảm ơn bạn đã nhắn tin. Hiện tại tính năng AI đang chạy ở chế độ giả lập (Mock).",
            confidence=0.8,
            intent="general"
        )

from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
import re
import unicodedata

# --- Session Schemas ---
class ChatSessionCreate(BaseModel):
    visitor_id: str = Field(..., min_length=1, max_length=255)
    customer_name: Optional[str] = Field(None, max_length=255)
    customer_email: Optional[str] = Field(None, max_length=255)

    @field_validator("customer_name", "customer_email")
    @classmethod
    def normalize_optional_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = unicodedata.normalize("NFKC", value).strip()
        return value or None

    @field_validator("customer_email")
    @classmethod
    def validate_customer_email(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("Email liên hệ không hợp lệ")
        return value

class ChatSessionUpdate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)

class TitleGenerateRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)

class ChatSessionResponse(BaseModel):
    id: UUID
    visitor_id: str
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    title: Optional[str] = "New Chat"
    status: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# --- Message Schemas ---
class ChatMessageRequest(BaseModel):
    session_id: UUID
    content: str = Field(..., min_length=1, max_length=2000)
    product_id: Optional[int] = None

    @field_validator("content")
    @classmethod
    def content_must_not_be_blank(cls, value: str) -> str:
        value = unicodedata.normalize("NFKC", value)
        value = "".join(
            character
            for character in value
            if character in {"\n", "\t"}
            or not unicodedata.category(character).startswith("C")
        )
        value = re.sub(r"[ \t]+", " ", value)
        value = re.sub(r"\n{3,}", "\n\n", value).strip()
        if not value:
            raise ValueError("Tin nhắn không được để trống")
        return value

class ChatMessageResponse(BaseModel):
    id: int
    session_id: UUID
    role: str
    content: str
    confidence: Optional[float] = None
    response_time_ms: Optional[int] = None
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    intent: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ChatFlowResponse(BaseModel):
    message: ChatMessageResponse
    ticket_created: bool

from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

# --- Session Schemas ---
class ChatSessionCreate(BaseModel):
    visitor_id: str = Field(..., max_length=255)
    customer_name: Optional[str] = Field(None, max_length=255)
    customer_email: Optional[str] = Field(None, max_length=255)

class ChatSessionResponse(BaseModel):
    id: UUID
    visitor_id: str
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    status: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# --- Message Schemas ---
class ChatMessageRequest(BaseModel):
    session_id: UUID
    content: str
    product_id: Optional[int] = None

class ChatMessageResponse(BaseModel):
    id: int
    session_id: UUID
    role: str
    content: str
    confidence: Optional[float] = None
    response_time_ms: Optional[int] = None
    sources: List[Dict[str, Any]] = []
    intent: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ChatFlowResponse(BaseModel):
    message: ChatMessageResponse
    ticket_created: bool

from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime
from uuid import UUID

class TicketBase(BaseModel):
    session_id: UUID
    trigger_message_id: Optional[int] = None
    subject: str = Field(..., max_length=255)
    issue: str
    customer_name: Optional[str] = Field(None, max_length=255)
    customer_email: Optional[str] = Field(None, max_length=255)
    customer_phone: Optional[str] = Field(None, max_length=30)
    status: str = Field("pending", max_length=30)
    priority: str = Field("normal", max_length=30)
    staff_note: Optional[str] = None

class TicketCreate(TicketBase):
    pass

class TicketUpdate(BaseModel):
    subject: Optional[str] = Field(None, max_length=255)
    issue: Optional[str] = None
    customer_name: Optional[str] = Field(None, max_length=255)
    customer_email: Optional[str] = Field(None, max_length=255)
    customer_phone: Optional[str] = Field(None, max_length=30)
    status: Optional[str] = Field(None, max_length=30)
    priority: Optional[str] = Field(None, max_length=30)
    staff_note: Optional[str] = None
    resolved_at: Optional[datetime] = None

class TicketResponse(TicketBase):
    id: int
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

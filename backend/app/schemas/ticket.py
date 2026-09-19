from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Literal, Optional
from datetime import datetime
from uuid import UUID

TicketStatus = Literal["pending", "in_progress", "resolved", "closed"]
TicketPriority = Literal["low", "normal", "high", "urgent"]


class TicketBase(BaseModel):
    session_id: UUID
    trigger_message_id: Optional[int] = None
    subject: str = Field(..., min_length=1, max_length=255)
    issue: str = Field(..., min_length=1, max_length=10_000)
    customer_name: Optional[str] = Field(None, max_length=255)
    customer_email: Optional[str] = Field(None, max_length=255)
    customer_phone: Optional[str] = Field(None, max_length=30)
    status: TicketStatus = "pending"
    priority: TicketPriority = "normal"
    staff_note: Optional[str] = Field(None, max_length=10_000)

    model_config = ConfigDict(extra="forbid")

    @field_validator("subject", "issue")
    @classmethod
    def reject_blank_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

class TicketCreate(TicketBase):
    pass

class TicketUpdate(BaseModel):
    subject: Optional[str] = Field(None, min_length=1, max_length=255)
    issue: Optional[str] = Field(None, min_length=1, max_length=10_000)
    customer_name: Optional[str] = Field(None, max_length=255)
    customer_email: Optional[str] = Field(None, max_length=255)
    customer_phone: Optional[str] = Field(None, max_length=30)
    status: Optional[TicketStatus] = None
    priority: Optional[TicketPriority] = None
    staff_note: Optional[str] = Field(None, max_length=10_000)
    resolved_at: Optional[datetime] = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("subject", "issue")
    @classmethod
    def reject_blank_updated_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

class TicketResponse(TicketBase):
    id: int
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

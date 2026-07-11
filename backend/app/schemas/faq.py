from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime

class FAQBase(BaseModel):
    question: str = Field(..., description="Câu hỏi")
    answer: str = Field(..., description="Câu trả lời")
    category: str = Field(..., max_length=100)
    keywords: List[str] = Field(default_factory=list)
    is_active: bool = True

class FAQCreate(FAQBase):
    pass

class FAQUpdate(BaseModel):
    question: Optional[str] = None
    answer: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)
    keywords: Optional[List[str]] = None
    is_active: Optional[bool] = None

class FAQResponse(FAQBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

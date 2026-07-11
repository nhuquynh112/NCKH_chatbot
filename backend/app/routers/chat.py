from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from uuid import UUID
from app.database import get_db
from app.schemas.chat import (
    ChatSessionCreate, 
    ChatSessionResponse, 
    ChatMessageRequest, 
    ChatMessageResponse,
    ChatFlowResponse
)
from app.schemas.common import APIResponse
from app.services.chat_service import get_chat_service

router = APIRouter(
    prefix="/api/chat",
    tags=["Chat"]
)

@router.post("/sessions", response_model=APIResponse[ChatSessionResponse], status_code=status.HTTP_201_CREATED)
def create_session(
    session_in: ChatSessionCreate,
    db: Session = Depends(get_db)
):
    service = get_chat_service(db)
    session = service.create_session(session_in)
    return APIResponse(
        success=True,
        message="Chat session created successfully",
        data=session
    )

@router.post("/messages", response_model=APIResponse[ChatFlowResponse], status_code=status.HTTP_201_CREATED)
async def send_message(
    request: ChatMessageRequest,
    db: Session = Depends(get_db)
):
    service = get_chat_service(db)
    message, ticket_created = await service.process_message(request)
    
    return APIResponse(
        success=True,
        message="Message processed successfully",
        data={
            "message": ChatMessageResponse.model_validate(message),
            "ticket_created": ticket_created
        }
    )

@router.get("/sessions/{session_id}/messages", response_model=APIResponse[Dict[str, Any]])
def get_session_messages(
    session_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    service = get_chat_service(db)
    messages = service.get_session_messages(session_id, skip=skip, limit=limit)
    
    return APIResponse(
        success=True,
        message="Messages retrieved successfully",
        data={
            "items": [ChatMessageResponse.model_validate(m) for m in messages],
            "total_returned": len(messages)
        }
    )

@router.patch("/sessions/{session_id}/close", response_model=APIResponse[ChatSessionResponse])
def close_session(
    session_id: UUID,
    db: Session = Depends(get_db)
):
    service = get_chat_service(db)
    session = service.close_session(session_id)
    return APIResponse(
        success=True,
        message="Chat session closed successfully",
        data=session
    )

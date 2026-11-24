from fastapi import APIRouter, Depends, Header, HTTPException, Query, Security, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from uuid import UUID
from app.database import get_db
from app.schemas.chat import (
    ChatSessionCreate, 
    ChatSessionResponse, 
    ChatSessionUpdate,
    TitleGenerateRequest,
    ChatMessageRequest, 
    ChatMessageResponse,
    ChatFlowResponse
)
from app.schemas.common import APIResponse
from app.services.chat_service import get_chat_service
from app.core.security import has_valid_admin_credentials, optional_security

router = APIRouter(
    prefix="/api/chat",
    tags=["Chat"]
)


def _require_matching_visitor(visitor_id: str, visitor_header: str | None) -> None:
    if not visitor_header or visitor_header != visitor_id:
        raise HTTPException(status_code=403, detail="Invalid visitor identity")


def _authorize_session(
    service,
    session_id: UUID,
    visitor_header: str | None,
    credentials: HTTPAuthorizationCredentials | None,
) -> None:
    if credentials is not None:
        if has_valid_admin_credentials(credentials):
            return
        raise HTTPException(status_code=401, detail="Invalid or expired admin token")
    if not visitor_header or len(visitor_header) > 255:
        raise HTTPException(status_code=403, detail="Visitor identity required")
    service.assert_session_owner(session_id, visitor_header)

@router.post("/sessions", response_model=APIResponse[ChatSessionResponse], status_code=status.HTTP_201_CREATED)
def create_session(
    session_in: ChatSessionCreate,
    visitor_header: str | None = Header(None, alias="X-Visitor-ID"),
    db: Session = Depends(get_db)
):
    _require_matching_visitor(session_in.visitor_id, visitor_header)
    service = get_chat_service(db)
    session = service.create_session(session_in)
    return APIResponse(
        success=True,
        message="Chat session created successfully",
        data=session
    )

@router.get("/sessions", response_model=APIResponse[List[ChatSessionResponse]])
def get_visitor_sessions(
    visitor_id: str = Query(..., description="The visitor ID to fetch sessions for"),
    limit: int = Query(50, ge=1, le=100),
    visitor_header: str | None = Header(None, alias="X-Visitor-ID"),
    db: Session = Depends(get_db)
):
    _require_matching_visitor(visitor_id, visitor_header)
    service = get_chat_service(db)
    sessions = service.get_sessions_by_visitor(visitor_id, limit=limit)
    return APIResponse(
        success=True,
        message="Sessions retrieved successfully",
        data=sessions
    )

@router.patch("/sessions/{session_id}", response_model=APIResponse[ChatSessionResponse])
def update_session(
    session_id: UUID,
    session_in: ChatSessionUpdate,
    visitor_header: str | None = Header(None, alias="X-Visitor-ID"),
    credentials: HTTPAuthorizationCredentials | None = Security(optional_security),
    db: Session = Depends(get_db)
):
    service = get_chat_service(db)
    _authorize_session(service, session_id, visitor_header, credentials)
    session = service.update_session_title(session_id, session_in.title)
    return APIResponse(
        success=True,
        message="Session updated successfully",
        data=session
    )

@router.delete("/sessions/{session_id}", response_model=APIResponse[None])
def delete_session(
    session_id: UUID,
    visitor_header: str | None = Header(None, alias="X-Visitor-ID"),
    credentials: HTTPAuthorizationCredentials | None = Security(optional_security),
    db: Session = Depends(get_db)
):
    service = get_chat_service(db)
    _authorize_session(service, session_id, visitor_header, credentials)
    service.delete_session(session_id)
    return APIResponse(
        success=True,
        message="Session deleted successfully",
        data=None
    )

@router.post("/sessions/{session_id}/generate-title", response_model=APIResponse[str])
async def generate_session_title(
    session_id: UUID,
    request: TitleGenerateRequest,
    visitor_header: str | None = Header(None, alias="X-Visitor-ID"),
    credentials: HTTPAuthorizationCredentials | None = Security(optional_security),
    db: Session = Depends(get_db)
):
    service = get_chat_service(db)
    _authorize_session(service, session_id, visitor_header, credentials)
    title = await service.generate_and_update_title(session_id, request.message)
    return APIResponse(
        success=True,
        message="Title generated successfully",
        data=title
    )

@router.post("/messages", response_model=APIResponse[ChatFlowResponse], status_code=status.HTTP_201_CREATED)
async def send_message(
    request: ChatMessageRequest,
    visitor_header: str | None = Header(None, alias="X-Visitor-ID"),
    credentials: HTTPAuthorizationCredentials | None = Security(optional_security),
    db: Session = Depends(get_db)
):
    service = get_chat_service(db)
    _authorize_session(service, request.session_id, visitor_header, credentials)
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
    visitor_header: str | None = Header(None, alias="X-Visitor-ID"),
    credentials: HTTPAuthorizationCredentials | None = Security(optional_security),
    db: Session = Depends(get_db)
):
    service = get_chat_service(db)
    _authorize_session(service, session_id, visitor_header, credentials)
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
    visitor_header: str | None = Header(None, alias="X-Visitor-ID"),
    credentials: HTTPAuthorizationCredentials | None = Security(optional_security),
    db: Session = Depends(get_db)
):
    service = get_chat_service(db)
    _authorize_session(service, session_id, visitor_header, credentials)
    session = service.close_session(session_id)
    return APIResponse(
        success=True,
        message="Chat session closed successfully",
        data=session
    )

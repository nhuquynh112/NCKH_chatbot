from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from app.database import get_db
from app.schemas.ticket import TicketCreate, TicketUpdate, TicketResponse
from app.schemas.common import APIResponse
from app.services.ticket_service import get_ticket_service
from app.core.security import verify_admin_token

router = APIRouter(
    prefix="/api/tickets",
    tags=["Tickets"]
)

@router.post("", response_model=APIResponse[TicketResponse], status_code=status.HTTP_201_CREATED)
def create_ticket(
    ticket_in: TicketCreate,
    db: Session = Depends(get_db)
):
    service = get_ticket_service(db)
    ticket = service.create_ticket(ticket_in)
    return APIResponse(
        success=True,
        message="Ticket created successfully",
        data=ticket
    )

@router.get("", response_model=APIResponse[Dict[str, Any]])
def list_tickets(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    priority_filter: Optional[str] = Query(None, alias="priority", description="Filter by priority"),
    db: Session = Depends(get_db),
    admin: str = Depends(verify_admin_token)
):
    service = get_ticket_service(db)
    tickets, total = service.list_tickets(
        page=page,
        page_size=page_size,
        status_filter=status_filter,
        priority_filter=priority_filter
    )
    
    return APIResponse(
        success=True,
        message="Tickets retrieved successfully",
        data={
            "items": [TicketResponse.model_validate(t) for t in tickets],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if total > 0 else 0
        }
    )

@router.get("/{ticket_id}", response_model=APIResponse[TicketResponse])
def get_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    admin: str = Depends(verify_admin_token)
):
    service = get_ticket_service(db)
    ticket = service.get_ticket(ticket_id)
    return APIResponse(
        success=True,
        message="Ticket retrieved successfully",
        data=ticket
    )

@router.patch("/{ticket_id}", response_model=APIResponse[TicketResponse])
def update_ticket(
    ticket_id: int,
    ticket_in: TicketUpdate,
    db: Session = Depends(get_db),
    admin: str = Depends(verify_admin_token)
):
    service = get_ticket_service(db)
    ticket = service.update_ticket(ticket_id, ticket_in)
    return APIResponse(
        success=True,
        message="Ticket updated successfully",
        data=ticket
    )

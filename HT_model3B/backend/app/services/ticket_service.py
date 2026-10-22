from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.repositories.ticket_repository import TicketRepository
from app.schemas.ticket import TicketCreate, TicketUpdate
from app.models import Ticket

def utc_now():
    return datetime.now(timezone.utc)

class TicketService:
    def __init__(self, db: Session):
        self.repository = TicketRepository(db)

    def get_ticket(self, ticket_id: int) -> Ticket:
        ticket = self.repository.get_by_id(ticket_id)
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ticket with id {ticket_id} not found."
            )
        return ticket

    def list_tickets(
        self,
        page: int = 1,
        page_size: int = 10,
        status_filter: Optional[str] = None,
        priority_filter: Optional[str] = None
    ) -> Tuple[List[Ticket], int]:
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 10
            
        skip = (page - 1) * page_size
        return self.repository.get_all(
            skip=skip,
            limit=page_size,
            status=status_filter,
            priority=priority_filter
        )

    def create_ticket(self, ticket_in: TicketCreate) -> Ticket:
        return self.repository.create(ticket_in)

    def update_ticket(self, ticket_id: int, ticket_in: TicketUpdate) -> Ticket:
        ticket = self.get_ticket(ticket_id)
        
        # Auto set resolved_at if status changes to resolved/closed
        if ticket_in.status in ["resolved", "closed"] and ticket.status not in ["resolved", "closed"]:
            ticket_in.resolved_at = utc_now()
            
        return self.repository.update(ticket, ticket_in)


def get_ticket_service(db: Session) -> TicketService:
    return TicketService(db)

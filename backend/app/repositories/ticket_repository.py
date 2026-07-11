from sqlalchemy.orm import Session
from typing import List, Optional, Tuple
from app.models import Ticket
from app.schemas.ticket import TicketCreate, TicketUpdate

class TicketRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, ticket_id: int) -> Optional[Ticket]:
        return self.db.query(Ticket).filter(Ticket.id == ticket_id).first()

    def get_all(
        self,
        skip: int = 0,
        limit: int = 10,
        status: Optional[str] = None,
        priority: Optional[str] = None
    ) -> Tuple[List[Ticket], int]:
        query = self.db.query(Ticket)
        
        if status:
            query = query.filter(Ticket.status == status)
        if priority:
            query = query.filter(Ticket.priority == priority)

        total = query.count()
        tickets = query.offset(skip).limit(limit).all()
        return tickets, total

    def create(self, ticket_in: TicketCreate) -> Ticket:
        db_ticket = Ticket(**ticket_in.model_dump())
        self.db.add(db_ticket)
        self.db.commit()
        self.db.refresh(db_ticket)
        return db_ticket

    def update(self, db_ticket: Ticket, ticket_in: TicketUpdate) -> Ticket:
        update_data = ticket_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_ticket, field, value)
        
        self.db.commit()
        self.db.refresh(db_ticket)
        return db_ticket

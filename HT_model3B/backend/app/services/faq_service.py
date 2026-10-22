from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.repositories.faq_repository import FAQRepository
from app.schemas.faq import FAQCreate, FAQUpdate
from app.models import FAQ

class FAQService:
    def __init__(self, db: Session):
        self.repository = FAQRepository(db)

    def get_faq(self, faq_id: int) -> FAQ:
        faq = self.repository.get_by_id(faq_id)
        if not faq:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"FAQ with id {faq_id} not found."
            )
        return faq

    def list_faqs(
        self,
        page: int = 1,
        page_size: int = 10,
        search: Optional[str] = None,
        category: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Tuple[List[FAQ], int]:
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 10
            
        skip = (page - 1) * page_size
        return self.repository.get_all(
            skip=skip,
            limit=page_size,
            search=search,
            category=category,
            is_active=is_active
        )

    def create_faq(self, faq_in: FAQCreate) -> FAQ:
        return self.repository.create(faq_in)

    def update_faq(self, faq_id: int, faq_in: FAQUpdate) -> FAQ:
        faq = self.get_faq(faq_id)
        return self.repository.update(faq, faq_in)

    def delete_faq(self, faq_id: int) -> FAQ:
        faq = self.get_faq(faq_id)
        return self.repository.delete(faq)

def get_faq_service(db: Session) -> FAQService:
    return FAQService(db)

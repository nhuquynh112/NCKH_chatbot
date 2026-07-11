from sqlalchemy.orm import Session
from typing import List, Optional, Tuple
from app.models import FAQ
from app.schemas.faq import FAQCreate, FAQUpdate

class FAQRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, faq_id: int) -> Optional[FAQ]:
        return self.db.query(FAQ).filter(FAQ.id == faq_id).first()

    def get_all(
        self,
        skip: int = 0,
        limit: int = 10,
        search: Optional[str] = None,
        category: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Tuple[List[FAQ], int]:
        query = self.db.query(FAQ)
        
        if search:
            query = query.filter(FAQ.question.ilike(f"%{search}%"))
        if category:
            query = query.filter(FAQ.category == category)
        if is_active is not None:
            query = query.filter(FAQ.is_active == is_active)

        total = query.count()
        faqs = query.offset(skip).limit(limit).all()
        return faqs, total

    def create(self, faq_in: FAQCreate) -> FAQ:
        db_faq = FAQ(**faq_in.model_dump())
        self.db.add(db_faq)
        self.db.commit()
        self.db.refresh(db_faq)
        return db_faq

    def update(self, db_faq: FAQ, faq_in: FAQUpdate) -> FAQ:
        update_data = faq_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_faq, field, value)
        
        self.db.commit()
        self.db.refresh(db_faq)
        return db_faq

    def delete(self, db_faq: FAQ) -> FAQ:
        # Soft delete
        db_faq.is_active = False
        self.db.commit()
        self.db.refresh(db_faq)
        return db_faq

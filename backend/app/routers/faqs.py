from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from app.database import get_db
from app.schemas.faq import FAQCreate, FAQUpdate, FAQResponse
from app.schemas.common import APIResponse
from app.services.faq_service import get_faq_service
from app.core.security import verify_admin_token

router = APIRouter(
    prefix="/api/faqs",
    tags=["FAQs"]
)

@router.post("", response_model=APIResponse[FAQResponse], status_code=status.HTTP_201_CREATED)
def create_faq(
    faq_in: FAQCreate,
    db: Session = Depends(get_db),
    admin: str = Depends(verify_admin_token)
):
    service = get_faq_service(db)
    faq = service.create_faq(faq_in)
    return APIResponse(
        success=True,
        message="FAQ created successfully",
        data=faq
    )

@router.get("", response_model=APIResponse[Dict[str, Any]])
def list_faqs(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by question"),
    category: Optional[str] = Query(None, description="Filter by category"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db)
):
    service = get_faq_service(db)
    faqs, total = service.list_faqs(
        page=page,
        page_size=page_size,
        search=search,
        category=category,
        is_active=is_active
    )
    
    return APIResponse(
        success=True,
        message="FAQs retrieved successfully",
        data={
            "items": [FAQResponse.model_validate(f) for f in faqs],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if total > 0 else 0
        }
    )

@router.get("/{faq_id}", response_model=APIResponse[FAQResponse])
def get_faq(
    faq_id: int,
    db: Session = Depends(get_db)
):
    service = get_faq_service(db)
    faq = service.get_faq(faq_id)
    return APIResponse(
        success=True,
        message="FAQ retrieved successfully",
        data=faq
    )

@router.put("/{faq_id}", response_model=APIResponse[FAQResponse])
def update_faq(
    faq_id: int,
    faq_in: FAQUpdate,
    db: Session = Depends(get_db),
    admin: str = Depends(verify_admin_token)
):
    service = get_faq_service(db)
    faq = service.update_faq(faq_id, faq_in)
    return APIResponse(
        success=True,
        message="FAQ updated successfully",
        data=faq
    )

@router.delete("/{faq_id}", response_model=APIResponse[FAQResponse])
def delete_faq(
    faq_id: int,
    db: Session = Depends(get_db),
    admin: str = Depends(verify_admin_token)
):
    service = get_faq_service(db)
    faq = service.delete_faq(faq_id)
    return APIResponse(
        success=True,
        message="FAQ deleted successfully (soft delete)",
        data=faq
    )

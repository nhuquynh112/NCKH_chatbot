from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from app.database import get_db
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse
from app.schemas.common import APIResponse
from app.services.product_service import get_product_service
from app.core.security import verify_admin_token

router = APIRouter(
    prefix="/api/products",
    tags=["Products"]
)

@router.post("", response_model=APIResponse[ProductResponse], status_code=status.HTTP_201_CREATED)
def create_product(
    product_in: ProductCreate,
    db: Session = Depends(get_db),
    admin: str = Depends(verify_admin_token)
):
    service = get_product_service(db)
    product = service.create_product(product_in)
    return APIResponse(
        success=True,
        message="Product created successfully",
        data=product
    )

@router.get("", response_model=APIResponse[Dict[str, Any]])
def list_products(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by product name"),
    category: Optional[str] = Query(None, description="Filter by category"),
    brand: Optional[str] = Query(None, description="Filter by brand"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db)
):
    service = get_product_service(db)
    products, total = service.list_products(
        page=page,
        page_size=page_size,
        search=search,
        category=category,
        brand=brand,
        is_active=is_active
    )
    
    return APIResponse(
        success=True,
        message="Products retrieved successfully",
        data={
            "items": [ProductResponse.model_validate(p) for p in products],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if total > 0 else 0
        }
    )

@router.get("/{product_id}", response_model=APIResponse[ProductResponse])
def get_product(
    product_id: int,
    db: Session = Depends(get_db)
):
    service = get_product_service(db)
    product = service.get_product(product_id)
    return APIResponse(
        success=True,
        message="Product retrieved successfully",
        data=product
    )

@router.put("/{product_id}", response_model=APIResponse[ProductResponse])
def update_product(
    product_id: int,
    product_in: ProductUpdate,
    db: Session = Depends(get_db),
    admin: str = Depends(verify_admin_token)
):
    service = get_product_service(db)
    product = service.update_product(product_id, product_in)
    return APIResponse(
        success=True,
        message="Product updated successfully",
        data=product
    )

@router.delete("/{product_id}", response_model=APIResponse[ProductResponse])
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    admin: str = Depends(verify_admin_token)
):
    service = get_product_service(db)
    product = service.delete_product(product_id)
    return APIResponse(
        success=True,
        message="Product deleted successfully (soft delete)",
        data=product
    )

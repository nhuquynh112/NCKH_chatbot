from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.repositories.product_repository import ProductRepository
from app.schemas.product import ProductCreate, ProductUpdate
from app.models import Product

class ProductService:
    def __init__(self, db: Session):
        self.repository = ProductRepository(db)

    def get_product(self, product_id: int) -> Product:
        product = self.repository.get_by_id(product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with id {product_id} not found."
            )
        return product

    def list_products(
        self,
        page: int = 1,
        page_size: int = 10,
        search: Optional[str] = None,
        category: Optional[str] = None,
        brand: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Tuple[List[Product], int]:
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
            brand=brand,
            is_active=is_active
        )

    def create_product(self, product_in: ProductCreate) -> Product:
        existing_product = self.repository.get_by_slug(product_in.slug)
        if existing_product:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Product with slug '{product_in.slug}' already exists."
            )
        return self.repository.create(product_in)

    def update_product(self, product_id: int, product_in: ProductUpdate) -> Product:
        product = self.get_product(product_id)
        
        if product_in.slug and product_in.slug != product.slug:
            existing_product = self.repository.get_by_slug(product_in.slug)
            if existing_product:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Product with slug '{product_in.slug}' already exists."
                )
                
        return self.repository.update(product, product_in)

    def delete_product(self, product_id: int) -> Product:
        product = self.get_product(product_id)
        return self.repository.delete(product)

def get_product_service(db: Session) -> ProductService:
    return ProductService(db)

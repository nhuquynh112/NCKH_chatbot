from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional, Tuple
from app.models import Product
from app.schemas.product import ProductCreate, ProductUpdate

class ProductRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, product_id: int) -> Optional[Product]:
        return self.db.query(Product).filter(Product.id == product_id).first()

    def get_by_slug(self, slug: str) -> Optional[Product]:
        return self.db.query(Product).filter(Product.slug == slug).first()

    def get_all(
        self,
        skip: int = 0,
        limit: int = 10,
        search: Optional[str] = None,
        category: Optional[str] = None,
        brand: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Tuple[List[Product], int]:
        query = self.db.query(Product)
        
        if search:
            query = query.filter(
                or_(
                    Product.name.ilike(f"%{search}%"),
                    Product.category.ilike(f"%{search}%"),
                    Product.brand.ilike(f"%{search}%")
                )
            )
        if category:
            query = query.filter(Product.category == category)
        if brand:
            query = query.filter(Product.brand == brand)
        if is_active is not None:
            query = query.filter(Product.is_active == is_active)

        total = query.count()
        products = query.order_by(Product.id.asc()).offset(skip).limit(limit).all()
        return products, total

    def create(self, product_in: ProductCreate) -> Product:
        db_product = Product(**product_in.model_dump())
        self.db.add(db_product)
        self.db.commit()
        self.db.refresh(db_product)
        return db_product

    def update(self, db_product: Product, product_in: ProductUpdate) -> Product:
        update_data = product_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_product, field, value)
        
        self.db.commit()
        self.db.refresh(db_product)
        return db_product

    def delete(self, db_product: Product) -> Product:
        # Soft delete
        db_product.is_active = False
        self.db.commit()
        self.db.refresh(db_product)
        return db_product

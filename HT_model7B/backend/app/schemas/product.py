from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import Optional, Dict, Any
from datetime import datetime

class ProductBase(BaseModel):
    name: str = Field(..., max_length=255)
    slug: str = Field(..., max_length=255)
    category: str = Field(..., max_length=100)
    brand: Optional[str] = Field(None, max_length=100)
    description: str
    price: float = Field(0.0, ge=0.0)
    warranty_months: Optional[int] = Field(None, ge=0)
    specifications: Dict[str, Any] = Field(default_factory=dict)
    image_url: Optional[str] = None
    is_active: bool = True

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    slug: Optional[str] = Field(None, max_length=255)
    category: Optional[str] = Field(None, max_length=100)
    brand: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    price: Optional[float] = Field(None, ge=0.0)
    warranty_months: Optional[int] = Field(None, ge=0)
    specifications: Optional[Dict[str, Any]] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = None

class ProductResponse(ProductBase):
    id: int
    created_at: datetime
    updated_at: datetime
    source_urls: list[dict[str, str]] = Field(default_factory=list)
    verification_status: str = "store_catalog_only"
    price_basis: Optional[str] = None
    collected_at: Optional[str] = None
    warranty_source_text: Optional[str] = None
    selected_color: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def attach_source_metadata(cls, value):
        from app.product_enrichment import merge_verified_product
        if isinstance(value, dict):
            data = dict(value)
        else:
            data = {name: getattr(value, name) for name in cls.model_fields if hasattr(value, name)}
        return merge_verified_product(data, preserve_store_fields=True)

    model_config = ConfigDict(from_attributes=True)

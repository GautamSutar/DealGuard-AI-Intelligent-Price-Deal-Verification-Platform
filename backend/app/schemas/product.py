from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class ProductSchema(BaseModel):
    id: UUID
    canonical_name: str
    brand: Optional[str] = None
    model: Optional[str] = None
    category: Optional[str] = None
    image_url: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ProductListingSchema(BaseModel):
    id: UUID
    product_id: UUID
    marketplace_name: str
    external_product_id: str
    url: Optional[str] = None
    title: str
    image_url: Optional[str] = None
    variant_description: Optional[str] = None
    availability: bool
    currency: str
    last_checked_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ProductSearchResult(BaseModel):
    """Returned to frontend after a product search."""

    listing_id: UUID
    product_id: UUID
    marketplace: str
    title: str
    brand: Optional[str] = None
    image_url: Optional[str] = None
    external_product_id: str
    url: Optional[str] = None
    current_price: Optional[float] = None
    mrp: Optional[float] = None
    effective_price: Optional[float] = None
    currency: str = "INR"
    availability: bool = True
    last_checked_at: Optional[datetime] = None


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=500, description="Product name or marketplace URL")
    marketplace: Optional[str] = Field(None, description="Filter to specific marketplace: amazon | flipkart")
    session_id: Optional[str] = None


class TrackProductRequest(BaseModel):
    external_product_id: str
    marketplace: str  # "amazon" | "flipkart"
    url: Optional[str] = None

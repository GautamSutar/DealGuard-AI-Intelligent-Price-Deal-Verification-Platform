from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class CurrentPriceSchema(BaseModel):
    listing_id: UUID
    marketplace: str
    title: str
    mrp: Optional[float] = None
    selling_price: float
    effective_price: Optional[float] = None
    currency: str = "INR"
    availability: bool
    source: str
    observed_at: datetime
    last_checked_at: Optional[datetime] = None


class PriceHistorySchema(BaseModel):
    id: UUID
    product_listing_id: UUID
    observed_at: datetime
    mrp: Optional[float] = None
    selling_price: float
    effective_price: Optional[float] = None
    currency: str
    availability: bool
    source_type: str
    source_reference: Optional[str] = None
    confidence_score: Optional[float] = None

    model_config = {"from_attributes": True}


class PriceHistoryPoint(BaseModel):
    """Lightweight point for chart rendering."""

    date: str
    price: float
    source: str

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class OfferSchema(BaseModel):
    id: UUID
    product_listing_id: UUID
    offer_type: str
    title: Optional[str] = None
    description: Optional[str] = None
    discount_value: Optional[float] = None
    discount_percentage: Optional[float] = None
    coupon_code: Optional[str] = None
    eligibility: Optional[str] = None
    conditions: Optional[str] = None
    is_conditional: bool = False
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    source: Optional[str] = None

    model_config = {"from_attributes": True}


class EffectivePriceBreakdown(BaseModel):
    """Shows how effective price is computed — conditionals stay separate."""

    base_selling_price: float
    public_coupon_discount: float = 0.0
    base_effective_price: float  # selling_price - unconditional discounts only
    conditional_offers: list[OfferSchema] = []
    conditional_effective_price: Optional[float] = None  # only if conditions met
    currency: str = "INR"
    note: str = "Conditional offers (bank, exchange, etc.) require eligibility verification."

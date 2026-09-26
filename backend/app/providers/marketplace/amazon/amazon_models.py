"""Internal data models for Amazon provider responses."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class AmazonRawProduct:
    asin: str
    title: str
    url: str
    brand: Optional[str] = None
    image_url: Optional[str] = None
    mrp: Optional[float] = None
    price: Optional[float] = None
    currency: str = "INR"
    availability: bool = True
    seller_name: Optional[str] = None
    variant: Optional[str] = None
    raw_offers: List[dict] = field(default_factory=list)


@dataclass
class AmazonRawOffer:
    offer_type: str
    title: str
    discount_value: Optional[float] = None
    discount_percentage: Optional[float] = None
    coupon_code: Optional[str] = None
    eligibility: Optional[str] = None
    is_conditional: bool = False

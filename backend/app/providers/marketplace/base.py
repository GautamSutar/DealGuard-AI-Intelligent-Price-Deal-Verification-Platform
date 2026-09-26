"""
Base abstractions for marketplace providers.

Each marketplace (Amazon, Flipkart, …) implements MarketplaceProvider.
The rest of the application only ever talks to this interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class ProviderOffer:
    offer_type: str  # coupon | bank | exchange | membership | app_only | seller | bundle
    title: str
    discount_value: Optional[float] = None
    discount_percentage: Optional[float] = None
    coupon_code: Optional[str] = None
    eligibility: Optional[str] = None
    conditions: Optional[str] = None
    is_conditional: bool = False
    source: str = ""


@dataclass
class ProviderProduct:
    """Normalised product returned by any marketplace provider."""

    marketplace: str
    external_id: str
    title: str
    url: Optional[str] = None
    brand: Optional[str] = None
    variant: Optional[str] = None
    image_url: Optional[str] = None

    mrp: Optional[float] = None
    selling_price: Optional[float] = None
    effective_price: Optional[float] = None
    currency: str = "INR"

    seller_name: Optional[str] = None
    seller_id: Optional[str] = None
    availability: bool = True

    offers: List[ProviderOffer] = field(default_factory=list)
    observed_at: Optional[datetime] = None

    # Provenance
    source: str = ""
    confidence: float = 1.0


@dataclass
class ProviderHistoryRecord:
    external_id: str
    marketplace: str
    observed_at: datetime
    selling_price: float
    mrp: Optional[float] = None
    effective_price: Optional[float] = None
    currency: str = "INR"
    source: str = ""
    confidence: float = 1.0


class MarketplaceProvider(ABC):
    """Interface every marketplace provider must implement."""

    @abstractmethod
    async def search_products(self, query: str, limit: int = 10) -> List[ProviderProduct]:
        """Search for products by natural-language query."""

    @abstractmethod
    async def get_product(self, external_id: str) -> Optional[ProviderProduct]:
        """Retrieve a single product by its marketplace ID."""

    @abstractmethod
    async def get_current_offers(self, external_id: str) -> List[ProviderOffer]:
        """Retrieve active offers for a product."""

    @abstractmethod
    async def get_product_from_url(self, url: str) -> Optional[ProviderProduct]:
        """Parse a marketplace URL and retrieve the product."""

    @property
    @abstractmethod
    def marketplace_name(self) -> str:
        """Short identifier: 'amazon' | 'flipkart' etc."""

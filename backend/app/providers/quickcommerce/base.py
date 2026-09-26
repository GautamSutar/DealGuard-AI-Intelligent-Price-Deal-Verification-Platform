"""
Base abstraction for quick commerce providers.

Quick commerce (Blinkit, Zepto, Swiggy Instamart, BigBasket Now)
differs from traditional marketplace providers in three key ways:

  1. Location-gated — availability and price depend on the delivery
     dark store serving the buyer's pin code or lat/lon.
  2. Multi-platform — one API key typically covers all platforms.
  3. High volatility — prices and stock change within hours.

The QCProduct dataclass normalises the response from any platform
into a single shape so the price engine can compare them uniformly.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class QCProduct:
    """Normalised quick commerce product."""

    platform: str           # blinkit | zepto | swiggy_instamart | bigbasket_now
    external_id: str        # platform's SKU / item id
    name: str
    brand: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None       # "500ml", "1kg", "6 pack"

    price: Optional[float] = None    # current selling price (INR)
    mrp: Optional[float] = None      # maximum retail price (INR)
    discount_percent: Optional[float] = None

    in_stock: bool = True
    image_url: Optional[str] = None
    url: Optional[str] = None

    delivery_minutes: Optional[int] = None   # estimated delivery time

    lat: Optional[float] = None     # query coordinates (for provenance)
    lon: Optional[float] = None

    observed_at: Optional[datetime] = None
    source: str = ""
    confidence: float = 1.0

    tags: List[str] = field(default_factory=list)


class QuickCommerceProvider(ABC):
    """
    Interface every quick commerce provider must implement.
    All methods receive lat/lon because availability is location-gated.
    """

    @abstractmethod
    async def search(
        self,
        query: str,
        lat: float,
        lon: float,
        platform: Optional[str] = None,
        limit: int = 20,
    ) -> List[QCProduct]:
        """
        Search for products by name/keyword across one or all platforms.
        platform=None means all available platforms.
        """

    @abstractmethod
    async def get_item(
        self,
        item_id: str,
        platform: str,
        lat: float,
        lon: float,
    ) -> Optional[QCProduct]:
        """Retrieve a single item by its platform-specific ID."""

    @abstractmethod
    async def compare_price(
        self,
        query: str,
        lat: float,
        lon: float,
    ) -> List[QCProduct]:
        """
        Search across ALL platforms and return results grouped/sorted
        by price so the caller can show the cheapest source.
        """

    @property
    @abstractmethod
    def supported_platforms(self) -> List[str]:
        """List of platform names this provider can query."""

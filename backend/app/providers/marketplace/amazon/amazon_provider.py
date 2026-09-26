"""
Amazon marketplace provider.

Selects implementation based on AMAZON_PROVIDER env var:
  - 'mock'  : returns realistic test data (no API key needed for dev)
  - 'keepa' : uses Keepa API (requires KEEPA_API_KEY)

To add a new backend, subclass AmazonBaseProvider and register it in
get_amazon_provider().
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import structlog

from app.config import settings
from app.providers.marketplace.amazon.amazon_models import AmazonRawProduct
from app.providers.marketplace.amazon.amazon_parser import parse_asin_from_url, parse_amazon_product
from app.providers.marketplace.base import MarketplaceProvider, ProviderOffer, ProviderProduct

logger = structlog.get_logger(__name__)


class AmazonMockProvider(MarketplaceProvider):
    """
    Development mock that returns plausible but synthetic data.
    Replace with a real provider once you have API access.
    All prices, offers, and history are SYNTHETIC — never present them as real.
    """

    MOCK_PRODUCTS = {
        "iphone-16-128gb": {
            "asin": "B0CHX1W1XY",
            "title": "Apple iPhone 16 (128 GB) - Black",
            "brand": "Apple",
            "variant": "128GB Black",
            "mrp": 79999.0,
            "price": 69999.0,
            "url": "https://www.amazon.in/dp/B0CHX1W1XY",
            "image_url": "https://m.media-amazon.com/images/placeholder.jpg",
            "raw_offers": [
                {"type": "coupon", "title": "Apply ₹2,000 coupon", "discount_value": 2000.0, "is_conditional": False},
                {
                    "type": "bank",
                    "title": "₹3,000 instant discount on HDFC credit card",
                    "discount_value": 3000.0,
                    "eligibility": "HDFC credit card",
                    "is_conditional": True,
                },
            ],
        },
        "samsung-tv-55": {
            "asin": "B0CSMP4B1J",
            "title": "Samsung 139 cm (55 inches) 4K Ultra HD Smart LED TV",
            "brand": "Samsung",
            "variant": "55 inch 4K",
            "mrp": 74900.0,
            "price": 44990.0,
            "url": "https://www.amazon.in/dp/B0CSMP4B1J",
            "image_url": "https://m.media-amazon.com/images/placeholder.jpg",
            "raw_offers": [],
        },
        "sony-wh1000xm5": {
            "asin": "B09XS7JWHH",
            "title": "Sony WH-1000XM5 Wireless Noise Cancelling Headphones",
            "brand": "Sony",
            "variant": "Black",
            "mrp": 29990.0,
            "price": 22990.0,
            "url": "https://www.amazon.in/dp/B09XS7JWHH",
            "image_url": "https://m.media-amazon.com/images/placeholder.jpg",
            "raw_offers": [
                {"type": "coupon", "title": "Apply ₹1,500 coupon", "discount_value": 1500.0, "is_conditional": False},
            ],
        },
    }

    @property
    def marketplace_name(self) -> str:
        return "amazon"

    async def search_products(self, query: str, limit: int = 10) -> List[ProviderProduct]:
        logger.info("Amazon mock: searching", query=query)
        query_lower = query.lower()
        results = []
        for key, data in self.MOCK_PRODUCTS.items():
            if any(word in data["title"].lower() for word in query_lower.split()):
                raw = AmazonRawProduct(**data)
                results.append(parse_amazon_product(raw, source="mock"))
        if not results:
            # Return first product as a fallback for demo purposes
            data = list(self.MOCK_PRODUCTS.values())[0]
            raw = AmazonRawProduct(**data)
            results.append(parse_amazon_product(raw, source="mock"))
        return results[:limit]

    async def get_product(self, external_id: str) -> Optional[ProviderProduct]:
        for data in self.MOCK_PRODUCTS.values():
            if data["asin"] == external_id:
                raw = AmazonRawProduct(**data)
                return parse_amazon_product(raw, source="mock")
        return None

    async def get_current_offers(self, external_id: str) -> List[ProviderOffer]:
        product = await self.get_product(external_id)
        return product.offers if product else []

    async def get_product_from_url(self, url: str) -> Optional[ProviderProduct]:
        asin = parse_asin_from_url(url)
        if asin:
            return await self.get_product(asin)
        return None


def get_amazon_provider() -> MarketplaceProvider:
    provider_name = settings.amazon_provider.lower()
    if provider_name == "mock":
        return AmazonMockProvider()
    # Future: elif provider_name == "keepa": return AmazonKeepaProvider()
    logger.warning("Unknown AMAZON_PROVIDER, falling back to mock", provider=provider_name)
    return AmazonMockProvider()

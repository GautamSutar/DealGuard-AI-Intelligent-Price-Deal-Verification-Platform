"""
Flipkart marketplace provider factory.

Selects implementation based on FLIPKART_PROVIDER env var:
  - 'reefapi' : live data via ReefAPI (requires REEFAPI_KEY)
  - 'mock'    : synthetic data for development (no key needed)

Add new backends by subclassing MarketplaceProvider and registering
them in get_flipkart_provider().
"""

from __future__ import annotations

from typing import List, Optional

import structlog

from app.config import settings
from app.providers.marketplace.base import (
    MarketplaceProvider,
    ProviderOffer,
    ProviderProduct,
)

logger = structlog.get_logger(__name__)


class FlipkartMockProvider(MarketplaceProvider):
    """
    Development mock — realistic but synthetic data.
    All prices are SYNTHETIC. Never present as real Flipkart prices.
    """

    MOCK_PRODUCTS = {
        "samsung-galaxy-s24": {
            "itm_id": "itm7c0281cd247be",
            "product_id": "MOBH4DQF849HCG6G",
            "title": "Samsung Galaxy S24 5G (Cobalt Violet, 8GB, 128GB)",
            "price": 59999.0,
            "mrp": 74999.0,
            "url": (
                "https://www.flipkart.com/samsung-galaxy-s24/"
                "p/itm7c0281cd247be?pid=MOBH4DQF849HCG6G"
            ),
            "image": "https://rukminim2.flixcart.com/placeholder.jpg",
            "in_stock": True,
            "raw_offers": [
                {
                    "type": "bank",
                    "title": "₹3,000 off on HDFC Bank Credit Card",
                    "amount": 3000.0,
                    "is_conditional": True,
                },
                {
                    "type": "exchange",
                    "title": "Up to ₹30,000 off on exchange",
                    "amount": 30000.0,
                    "is_conditional": True,
                },
            ],
        },
        "oneplus-12": {
            "itm_id": "itm9ab12ef34cd56",
            "product_id": "MOBH3XQPQR47ABCD",
            "title": "OnePlus 12 5G (Flowy Emerald, 12GB, 256GB)",
            "price": 64999.0,
            "mrp": 69999.0,
            "url": (
                "https://www.flipkart.com/oneplus-12/"
                "p/itm9ab12ef34cd56?pid=MOBH3XQPQR47ABCD"
            ),
            "image": "https://rukminim2.flixcart.com/placeholder.jpg",
            "in_stock": True,
            "raw_offers": [
                {
                    "type": "coupon",
                    "title": "Apply ₹2,000 coupon",
                    "amount": 2000.0,
                    "is_conditional": False,
                },
            ],
        },
    }

    @property
    def marketplace_name(self) -> str:
        return "flipkart"

    async def search_products(
        self, query: str, limit: int = 10
    ) -> List[ProviderProduct]:
        logger.info("Flipkart mock: search", query=query)
        query_lower = query.lower()
        results = []
        for data in self.MOCK_PRODUCTS.values():
            if any(
                w in data["title"].lower()
                for w in query_lower.split()
            ):
                results.append(self._to_product(data))
        if not results:
            results = [self._to_product(
                list(self.MOCK_PRODUCTS.values())[0]
            )]
        return results[:limit]

    async def get_product(
        self, external_id: str
    ) -> Optional[ProviderProduct]:
        for data in self.MOCK_PRODUCTS.values():
            if (
                data["itm_id"] == external_id
                or data["product_id"] == external_id
            ):
                return self._to_product(data)
        return None

    async def get_current_offers(
        self, external_id: str
    ) -> List[ProviderOffer]:
        product = await self.get_product(external_id)
        return product.offers if product else []

    async def get_product_from_url(
        self, url: str
    ) -> Optional[ProviderProduct]:
        for data in self.MOCK_PRODUCTS.values():
            if data["itm_id"] in url or data["product_id"] in url:
                return self._to_product(data)
        return None

    def _to_product(self, data: dict) -> ProviderProduct:
        from datetime import datetime, timezone

        offers = [
            ProviderOffer(
                offer_type=o["type"],
                title=o["title"],
                discount_value=o.get("amount"),
                is_conditional=o.get("is_conditional", False),
                source="mock",
            )
            for o in data.get("raw_offers", [])
        ]
        return ProviderProduct(
            marketplace="flipkart",
            external_id=data["itm_id"],
            title=data["title"],
            url=data["url"],
            image_url=data.get("image"),
            mrp=data.get("mrp"),
            selling_price=data["price"],
            effective_price=data["price"],
            currency="INR",
            availability=data.get("in_stock", True),
            offers=offers,
            observed_at=datetime.now(timezone.utc),
            source="mock",
            confidence=1.0,
        )


def get_flipkart_provider() -> MarketplaceProvider:
    provider_name = settings.flipkart_provider.lower()

    if provider_name == "reefapi":
        if not settings.reefapi_key:
            logger.warning(
                "REEFAPI_KEY not set — falling back to mock",
            )
            return FlipkartMockProvider()
        from app.providers.marketplace.flipkart.reefapi_provider import (
            ReefAPIFlipkartProvider,
        )
        logger.info("Using ReefAPI Flipkart provider")
        return ReefAPIFlipkartProvider()

    if provider_name == "mock":
        return FlipkartMockProvider()

    logger.warning(
        "Unknown FLIPKART_PROVIDER, falling back to mock",
        provider=provider_name,
    )
    return FlipkartMockProvider()

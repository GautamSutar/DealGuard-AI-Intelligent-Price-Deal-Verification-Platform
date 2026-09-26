"""
Flipkart marketplace provider — V2 placeholder.

Flipkart does not offer a public consumer product-search API.
This stub returns an informative error so the application degrades gracefully.
A real implementation will be added in Phase 10.
"""

from __future__ import annotations

from typing import List, Optional

import structlog

from app.providers.marketplace.base import MarketplaceProvider, ProviderOffer, ProviderProduct

logger = structlog.get_logger(__name__)


class FlipkartPlaceholderProvider(MarketplaceProvider):
    """Placeholder until a legitimate Flipkart data source is integrated."""

    @property
    def marketplace_name(self) -> str:
        return "flipkart"

    async def search_products(self, query: str, limit: int = 10) -> List[ProviderProduct]:
        logger.info("Flipkart provider: not yet implemented", query=query)
        return []

    async def get_product(self, external_id: str) -> Optional[ProviderProduct]:
        return None

    async def get_current_offers(self, external_id: str) -> List[ProviderOffer]:
        return []

    async def get_product_from_url(self, url: str) -> Optional[ProviderProduct]:
        return None


def get_flipkart_provider() -> MarketplaceProvider:
    return FlipkartPlaceholderProvider()

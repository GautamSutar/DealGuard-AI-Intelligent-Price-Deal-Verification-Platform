"""Product service — search, track, retrieve products."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.listing import ProductListing
from app.models.marketplace import Marketplace
from app.models.product import Product
from app.providers.marketplace.amazon.amazon_provider import get_amazon_provider
from app.providers.common.product_normalizer import normalise_title
from app.schemas.product import ProductSearchResult

logger = structlog.get_logger(__name__)

_AMAZON_URL_PATTERN = re.compile(r"amazon\.in|amazon\.com", re.IGNORECASE)
_FLIPKART_URL_PATTERN = re.compile(r"flipkart\.com", re.IGNORECASE)


def detect_query_type(query: str) -> str:
    if query.startswith("http") and _AMAZON_URL_PATTERN.search(query):
        return "amazon_url"
    if query.startswith("http") and _FLIPKART_URL_PATTERN.search(query):
        return "flipkart_url"
    if re.match(r"^B0[A-Z0-9]{8}$", query):
        return "asin"
    return "text"


async def search_products(
    db: AsyncSession,
    query: str,
    marketplace: Optional[str] = None,
) -> List[ProductSearchResult]:
    query_type = detect_query_type(query)
    logger.info("Product search", query=query, type=query_type)

    provider = get_amazon_provider()
    results = []

    if query_type == "amazon_url":
        product = await provider.get_product_from_url(query)
        raw_products = [product] if product else []
    elif query_type == "asin":
        product = await provider.get_product(query)
        raw_products = [product] if product else []
    else:
        raw_products = await provider.search_products(query)

    for p in raw_products:
        if p is None:
            continue
        listing = await _get_or_create_listing(db, p)

        results.append(
            ProductSearchResult(
                listing_id=listing.id,
                product_id=listing.product_id,
                marketplace="amazon",
                title=p.title,
                brand=p.brand,
                image_url=p.image_url,
                external_product_id=p.external_id,
                url=p.url,
                current_price=p.selling_price,
                mrp=p.mrp,
                effective_price=p.effective_price,
                currency=p.currency,
                availability=p.availability,
                last_checked_at=listing.last_checked_at,
            )
        )

    return results


async def _get_or_create_listing(db: AsyncSession, provider_product) -> ProductListing:
    """Find existing listing or create product + listing records."""
    existing = await db.execute(
        select(ProductListing).where(
            ProductListing.external_product_id == provider_product.external_id
        )
    )
    listing = existing.scalar_one_or_none()
    if listing:
        listing.last_checked_at = datetime.now(timezone.utc)
        await db.commit()
        return listing

    # Normalise product
    norm = normalise_title(provider_product.title)

    # Get or create marketplace
    mp_result = await db.execute(select(Marketplace).where(Marketplace.name == provider_product.marketplace))
    marketplace = mp_result.scalar_one_or_none()
    if not marketplace:
        marketplace = Marketplace(
            name=provider_product.marketplace,
            display_name=provider_product.marketplace.capitalize(),
            base_url="https://www.amazon.in" if provider_product.marketplace == "amazon" else "https://www.flipkart.com",
        )
        db.add(marketplace)
        await db.flush()

    # Create product
    product = Product(
        canonical_name=norm.canonical_name or provider_product.title,
        brand=norm.brand or provider_product.brand,
        model=None,
        category=None,
        image_url=provider_product.image_url,
    )
    db.add(product)
    await db.flush()

    # Create listing
    listing = ProductListing(
        product_id=product.id,
        marketplace_id=marketplace.id,
        external_product_id=provider_product.external_id,
        url=provider_product.url,
        title=provider_product.title,
        image_url=provider_product.image_url,
        variant_description=provider_product.variant,
        availability=provider_product.availability,
        currency=provider_product.currency,
        last_checked_at=datetime.now(timezone.utc),
    )
    db.add(listing)
    await db.commit()
    await db.refresh(listing)
    return listing

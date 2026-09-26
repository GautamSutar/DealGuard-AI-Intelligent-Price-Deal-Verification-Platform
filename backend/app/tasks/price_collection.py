"""
Celery tasks for price collection.

Every 6 hours (configured in celery_app.py):
  1. Fetch all tracked product listings
  2. Retrieve current price from marketplace provider
  3. Store new price history record
  4. Update listing.last_checked_at
  5. Trigger analysis recalculation
"""

from __future__ import annotations

import asyncio
import structlog

from app.celery_app import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(
    name="app.tasks.price_collection.collect_product_price",
    bind=True,
    max_retries=3,
    default_retry_delay=300,
)
def collect_product_price(self, listing_id: str) -> dict:
    """Collect current price for a single product listing."""
    return asyncio.get_event_loop().run_until_complete(_collect_price_async(listing_id))


async def _collect_price_async(listing_id: str) -> dict:
    from datetime import datetime, timezone
    from app.database import AsyncSessionLocal
    from app.models.listing import ProductListing
    from app.providers.marketplace.amazon.amazon_provider import get_amazon_provider
    from app.services.history_service import record_current_price

    async with AsyncSessionLocal() as db:
        listing = await db.get(ProductListing, listing_id)
        if not listing:
            return {"status": "error", "message": "Listing not found"}

        provider = get_amazon_provider()
        product = await provider.get_product(listing.external_product_id)

        if not product or product.selling_price is None:
            logger.warning("No price data from provider", listing_id=listing_id)
            return {"status": "no_data", "listing_id": listing_id}

        await record_current_price(
            db=db,
            listing_id=listing.id,
            selling_price=product.selling_price,
            mrp=product.mrp,
            effective_price=product.effective_price,
            currency=product.currency,
            source_type="our_collector",
        )

        listing.last_checked_at = datetime.now(timezone.utc)
        await db.commit()

        logger.info("Price collected", listing_id=listing_id, price=product.selling_price)
        return {"status": "success", "listing_id": listing_id, "price": product.selling_price}


@celery_app.task(name="app.tasks.price_collection.collect_all_tracked_prices")
def collect_all_tracked_prices() -> dict:
    """Scheduled task: collect prices for all tracked listings."""
    return asyncio.get_event_loop().run_until_complete(_collect_all_async())


async def _collect_all_async() -> dict:
    from sqlalchemy import select
    from app.database import AsyncSessionLocal
    from app.models.listing import ProductListing

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(ProductListing).where(ProductListing.availability == True))
        listings = result.scalars().all()

    for listing in listings:
        collect_product_price.delay(str(listing.id))

    logger.info("Queued price collection", count=len(listings))
    return {"queued": len(listings)}

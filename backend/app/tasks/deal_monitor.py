"""
Deal Monitor — scheduled Celery task.

Every 6 hours (via Celery Beat):
  1. Fetch all tracked product listings from DB
  2. Get current price + offers from marketplace provider
  3. Record new price in price_history
  4. Recalculate analysis (compare vs historical avg/min/max)
  5. Log a DEAL ALERT if price dropped significantly or hit a new low

This is the automated agent that keeps price history fresh and
surfaces good deals without any user action.
"""

from __future__ import annotations

import asyncio
import structlog

from app.celery_app import celery_app

logger = structlog.get_logger(__name__)

# Thresholds for deal alerts
GOOD_DEAL_THRESHOLD_PCT = -5.0   # 5% below historical average
NEW_LOW_THRESHOLD_PCT = 5.0      # within 5% of all-time low


@celery_app.task(
    name="app.tasks.deal_monitor.monitor_product_deals",
    bind=True,
    max_retries=2,
    default_retry_delay=120,
)
def monitor_product_deals(self, listing_id: str) -> dict:
    """
    Monitor a single product listing for deals.
    Fetches current price, records it, and checks if it's a good deal.
    """
    return asyncio.get_event_loop().run_until_complete(
        _monitor_async(listing_id)
    )


async def _monitor_async(listing_id: str) -> dict:
    from uuid import UUID
    from datetime import datetime, timezone

    from app.database import AsyncSessionLocal
    from app.models.listing import ProductListing
    from app.providers.marketplace.amazon.amazon_provider import get_amazon_provider
    from app.services.history_service import record_current_price
    from app.services.offer_service import get_listing_offers
    from app.services.analysis_service import get_or_calculate_analysis

    async with AsyncSessionLocal() as db:
        listing = await db.get(ProductListing, UUID(listing_id))
        if not listing:
            return {"status": "error", "message": "Listing not found"}

        # Step 1: Fetch current price from marketplace
        provider = get_amazon_provider()
        product = await provider.get_product(listing.external_product_id)

        if not product or product.selling_price is None:
            logger.warning(
                "Deal monitor: no price from provider",
                listing_id=listing_id,
                external_id=listing.external_product_id,
            )
            return {"status": "no_data", "listing_id": listing_id}

        # Step 2: Record the new price in price_history
        await record_current_price(
            db=db,
            listing_id=listing.id,
            selling_price=product.selling_price,
            mrp=product.mrp,
            effective_price=product.effective_price,
            currency=product.currency,
            source_type="deal_monitor",
        )

        listing.last_checked_at = datetime.now(timezone.utc)
        await db.commit()

        # Step 3: Recalculate analysis with fresh price
        analysis = await get_or_calculate_analysis(
            db, listing.id, force_recalculate=True
        )

        if not analysis:
            return {"status": "no_analysis", "listing_id": listing_id}

        # Step 4: Fetch current offers
        offers = await get_listing_offers(db, listing.id)
        offer_count = len(offers)
        conditional_offers = [o for o in offers if o.is_conditional]

        # Step 5: Check deal conditions
        pct_vs_avg = analysis.pct_vs_average or 0.0
        pct_vs_min = analysis.pct_vs_minimum or 0.0
        classification = analysis.classification or "UNKNOWN"

        is_good_deal = pct_vs_avg <= GOOD_DEAL_THRESHOLD_PCT
        near_all_time_low = pct_vs_min <= NEW_LOW_THRESHOLD_PCT

        if is_good_deal or near_all_time_low:
            logger.info(
                "DEAL ALERT",
                product=listing.title,
                current_price=product.selling_price,
                historical_avg=analysis.historical_average,
                pct_vs_avg=round(pct_vs_avg, 2),
                pct_vs_min=round(pct_vs_min, 2),
                classification=classification,
                offers=offer_count,
                conditional_offers=len(conditional_offers),
                trend=analysis.price_trend,
            )

        result = {
            "status": "success",
            "listing_id": listing_id,
            "product": listing.title,
            "current_price": product.selling_price,
            "historical_avg": analysis.historical_average,
            "pct_vs_avg": round(pct_vs_avg, 2),
            "pct_vs_min": round(pct_vs_min, 2),
            "classification": classification,
            "trend": analysis.price_trend,
            "offers_found": offer_count,
            "deal_alert": is_good_deal or near_all_time_low,
        }

        logger.info("Deal monitor complete", **result)
        return result


@celery_app.task(name="app.tasks.deal_monitor.run_deal_monitor_all")
def run_deal_monitor_all() -> dict:
    """
    Scheduled task: run deal monitor for every tracked product listing.
    Triggered by Celery Beat every 6 hours.
    """
    return asyncio.get_event_loop().run_until_complete(_monitor_all_async())


async def _monitor_all_async() -> dict:
    from sqlalchemy import select
    from app.database import AsyncSessionLocal
    from app.models.listing import ProductListing

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ProductListing).where(ProductListing.availability == True)
        )
        listings = result.scalars().all()

    logger.info("Deal monitor: queuing all listings", count=len(listings))
    for listing in listings:
        monitor_product_deals.delay(str(listing.id))

    return {"status": "queued", "count": len(listings)}

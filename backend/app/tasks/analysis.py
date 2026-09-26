"""Celery tasks for price analysis recalculation."""

import asyncio

import structlog

from app.celery_app import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(name="app.tasks.analysis.calculate_price_analysis")
def calculate_price_analysis(listing_id: str) -> dict:
    return asyncio.get_event_loop().run_until_complete(_calculate_async(listing_id))


async def _calculate_async(listing_id: str) -> dict:
    from uuid import UUID
    from app.database import AsyncSessionLocal
    from app.services.analysis_service import get_or_calculate_analysis

    async with AsyncSessionLocal() as db:
        result = await get_or_calculate_analysis(db, UUID(listing_id), force_recalculate=True)
        if result:
            logger.info("Analysis recalculated", listing_id=listing_id, classification=result.classification)
            return {"status": "success", "listing_id": listing_id, "classification": result.classification}
        return {"status": "no_data", "listing_id": listing_id}


@celery_app.task(name="app.tasks.analysis.refresh_stale_analyses")
def refresh_stale_analyses() -> dict:
    return asyncio.get_event_loop().run_until_complete(_refresh_all_async())


async def _refresh_all_async() -> dict:
    from sqlalchemy import select
    from app.database import AsyncSessionLocal
    from app.models.listing import ProductListing

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(ProductListing))
        listings = result.scalars().all()

    for listing in listings:
        calculate_price_analysis.delay(str(listing.id))

    return {"queued": len(listings)}

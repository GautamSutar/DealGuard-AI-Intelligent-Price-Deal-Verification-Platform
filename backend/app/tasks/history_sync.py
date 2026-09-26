"""Celery tasks for historical data sync."""

import asyncio
import structlog

from app.celery_app import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(name="app.tasks.history_sync.sync_history")
def sync_history(listing_id: str) -> dict:
    """Bootstrap or refresh historical data for a listing."""
    return asyncio.get_event_loop().run_until_complete(_sync_async(listing_id))


async def _sync_async(listing_id: str) -> dict:
    from uuid import UUID
    from app.database import AsyncSessionLocal
    from app.models.listing import ProductListing
    from app.services.history_service import bootstrap_history

    async with AsyncSessionLocal() as db:
        listing = await db.get(ProductListing, UUID(listing_id))
        if not listing:
            return {"status": "error", "message": "Listing not found"}
        await bootstrap_history(db, listing)
        return {"status": "success", "listing_id": listing_id}

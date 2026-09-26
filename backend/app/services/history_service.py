"""History service — stores and retrieves price history records."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.listing import ProductListing
from app.models.price_history import PriceHistory
from app.providers.historical.mock_historical import MockHistoricalProvider
from app.schemas.price import PriceHistoryPoint, PriceHistorySchema

logger = structlog.get_logger(__name__)


async def get_price_history(
    db: AsyncSession,
    listing_id: UUID,
    days: int = 365,
) -> List[PriceHistoryPoint]:
    """Returns price history points suitable for chart rendering."""
    result = await db.execute(
        select(PriceHistory)
        .where(PriceHistory.product_listing_id == listing_id)
        .order_by(PriceHistory.observed_at.asc())
    )
    rows = result.scalars().all()

    if not rows:
        # Bootstrap from mock historical provider for demo purposes
        listing = await db.get(ProductListing, listing_id)
        if listing:
            await bootstrap_history(db, listing)
            result2 = await db.execute(
                select(PriceHistory)
                .where(PriceHistory.product_listing_id == listing_id)
                .order_by(PriceHistory.observed_at.asc())
            )
            rows = result2.scalars().all()

    return [
        PriceHistoryPoint(
            date=r.observed_at.strftime("%Y-%m-%d"),
            price=float(r.selling_price),
            source=r.source_type,
        )
        for r in rows
    ]


async def bootstrap_history(db: AsyncSession, listing: ProductListing) -> None:
    """
    Populate price_history from the configured historical provider.
    Skips if history already exists.
    """
    existing = await db.execute(
        select(PriceHistory).where(PriceHistory.product_listing_id == listing.id).limit(1)
    )
    if existing.scalar_one_or_none():
        return

    provider = MockHistoricalProvider()
    records = await provider.get_history(
        external_id=listing.external_product_id,
        marketplace="amazon",
        days=365,
    )

    for r in records:
        row = PriceHistory(
            product_listing_id=listing.id,
            observed_at=r.observed_at,
            mrp=r.mrp,
            selling_price=r.selling_price,
            effective_price=r.effective_price,
            currency=r.currency,
            availability=True,
            source_type=r.source,
            source_reference=provider.provider_name,
            confidence_score=r.confidence,
        )
        db.add(row)

    await db.commit()
    logger.info("Bootstrapped price history", listing_id=str(listing.id), records=len(records))


async def record_current_price(
    db: AsyncSession,
    listing_id: UUID,
    selling_price: float,
    mrp: Optional[float] = None,
    effective_price: Optional[float] = None,
    currency: str = "INR",
    source_type: str = "our_collector",
) -> PriceHistory:
    row = PriceHistory(
        product_listing_id=listing_id,
        observed_at=datetime.now(timezone.utc),
        mrp=mrp,
        selling_price=selling_price,
        effective_price=effective_price or selling_price,
        currency=currency,
        availability=True,
        source_type=source_type,
        source_reference="dealguard",
        confidence_score=1.0,
    )
    db.add(row)
    await db.commit()
    return row

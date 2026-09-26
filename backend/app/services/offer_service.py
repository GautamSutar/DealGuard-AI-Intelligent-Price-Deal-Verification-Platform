"""Offer service — stores and retrieves offer records."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.offer import Offer
from app.providers.marketplace.base import ProviderOffer
from app.schemas.offer import EffectivePriceBreakdown, OfferSchema

logger = structlog.get_logger(__name__)


async def get_listing_offers(db: AsyncSession, listing_id: UUID) -> List[OfferSchema]:
    result = await db.execute(
        select(Offer).where(Offer.product_listing_id == listing_id)
    )
    offers = result.scalars().all()
    return [OfferSchema.model_validate(o) for o in offers]


async def upsert_offers(
    db: AsyncSession,
    listing_id: UUID,
    provider_offers: List[ProviderOffer],
) -> None:
    """Replaces current offers for a listing with the latest provider data."""
    existing = await db.execute(select(Offer).where(Offer.product_listing_id == listing_id))
    for row in existing.scalars().all():
        await db.delete(row)

    for po in provider_offers:
        offer = Offer(
            product_listing_id=listing_id,
            offer_type=po.offer_type,
            title=po.title,
            discount_value=po.discount_value,
            discount_percentage=po.discount_percentage,
            coupon_code=po.coupon_code,
            eligibility=po.eligibility,
            conditions=po.conditions,
            is_conditional=po.is_conditional,
            source=po.source,
        )
        db.add(offer)

    await db.commit()


def calculate_effective_price_breakdown(
    selling_price: float,
    offers: List[OfferSchema],
    currency: str = "INR",
) -> EffectivePriceBreakdown:
    """
    Separates unconditional coupon discounts from conditional offers.
    Only unconditional coupons are subtracted from the base price.
    """
    public_coupon_total = 0.0
    conditional = []

    for offer in offers:
        if not offer.is_conditional and offer.offer_type == "coupon" and offer.discount_value:
            public_coupon_total += offer.discount_value
        elif offer.is_conditional:
            conditional.append(offer)

    base_effective = selling_price - public_coupon_total

    conditional_discount = sum(
        o.discount_value for o in conditional if o.discount_value
    )
    conditional_effective = base_effective - conditional_discount if conditional_discount else None

    return EffectivePriceBreakdown(
        base_selling_price=selling_price,
        public_coupon_discount=public_coupon_total,
        base_effective_price=round(base_effective, 2),
        conditional_offers=conditional,
        conditional_effective_price=round(conditional_effective, 2) if conditional_effective else None,
        currency=currency,
    )

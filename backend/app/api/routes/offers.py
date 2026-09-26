from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.listing import ProductListing
from app.schemas.offer import EffectivePriceBreakdown
from app.services.offer_service import calculate_effective_price_breakdown, get_listing_offers

router = APIRouter()


@router.get("/products/{listing_id}/offers")
async def get_offers(
    listing_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Returns all active offers for a product listing.

    IMPORTANT: Conditional offers (bank, exchange, membership) are clearly
    labelled. They are NOT automatically subtracted from the base price.
    """
    listing = await db.get(ProductListing, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    offers = await get_listing_offers(db, listing_id)
    return {"listing_id": str(listing_id), "offers": offers}


@router.get("/products/{listing_id}/offers/breakdown", response_model=EffectivePriceBreakdown)
async def get_effective_price_breakdown(
    listing_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Returns a transparent breakdown showing how the effective price is computed.

    - base_effective_price: selling price minus UNCONDITIONAL coupons only
    - conditional_effective_price: further reduced by conditional offers IF eligible
    """
    from app.models.price_history import PriceHistory
    from sqlalchemy import select

    listing = await db.get(ProductListing, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    offers = await get_listing_offers(db, listing_id)

    result = await db.execute(
        select(PriceHistory)
        .where(PriceHistory.product_listing_id == listing_id)
        .order_by(PriceHistory.observed_at.desc())
        .limit(1)
    )
    latest_price = result.scalar_one_or_none()

    if not latest_price:
        raise HTTPException(status_code=404, detail="No price data found for this listing")

    return calculate_effective_price_breakdown(
        selling_price=float(latest_price.selling_price),
        offers=offers,
        currency=latest_price.currency,
    )

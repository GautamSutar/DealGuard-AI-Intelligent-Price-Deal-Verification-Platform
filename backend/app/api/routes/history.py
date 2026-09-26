from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.price import PriceHistoryPoint
from app.services.history_service import get_price_history

router = APIRouter()


@router.get("/products/{listing_id}/history", response_model=List[PriceHistoryPoint])
async def get_history(
    listing_id: UUID,
    days: int = Query(default=365, ge=7, le=1825, description="Number of days of history to return"),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns price history for a product listing.

    The response includes data source labels. Coverage may vary:
    - If bootstrapped from an external provider (e.g. Keepa): labelled 'external_api'
    - If collected by DealGuard: labelled 'our_collector'

    Do NOT assume all records represent live DealGuard-observed prices.
    The source field on each record clarifies provenance.
    """
    return await get_price_history(db, listing_id, days)

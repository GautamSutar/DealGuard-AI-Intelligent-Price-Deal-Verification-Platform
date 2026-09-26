from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.analysis import PriceAnalysisSchema
from app.services.analysis_service import get_or_calculate_analysis

router = APIRouter()


@router.get("/products/{listing_id}/analysis", response_model=PriceAnalysisSchema)
async def get_analysis(
    listing_id: UUID,
    refresh: bool = Query(default=False, description="Force recalculation from raw history"),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns the deterministic price analysis for a product listing.

    All statistics (average, median, min, max, trend, classification) are
    calculated by the DealGuard price engine — never by the LLM.

    classification values:
      NEAR_HISTORICAL_LOW | BELOW_HISTORICAL_AVERAGE | AROUND_HISTORICAL_AVERAGE |
      ABOVE_HISTORICAL_AVERAGE | NEW_DATA_INSUFFICIENT | PRICE_INCREASING |
      PRICE_DECREASING | PRICE_VOLATILE
    """
    # Ensure history is bootstrapped first
    from app.services.history_service import bootstrap_history
    from app.models.listing import ProductListing
    listing = await db.get(ProductListing, listing_id)
    if listing:
        await bootstrap_history(db, listing)

    result = await get_or_calculate_analysis(db, listing_id, force_recalculate=refresh)
    if not result:
        raise HTTPException(status_code=404, detail="Analysis could not be generated. Check if the product exists and has price history.")
    return result

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.listing import ProductListing
from app.schemas.product import ProductListingSchema, TrackProductRequest

router = APIRouter()


@router.get("/products/{listing_id}", response_model=ProductListingSchema)
async def get_product(
    listing_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    listing = await db.get(ProductListing, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Product listing not found")
    return ProductListingSchema.model_validate(listing)


@router.post("/products/track")
async def track_product(
    request: TrackProductRequest,
    db: AsyncSession = Depends(get_db),
):
    """Add a product to the tracking system so its price is collected on schedule."""
    from app.services.product_service import search_products
    results = await search_products(db, request.external_product_id, request.marketplace)
    if not results:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product is now being tracked", "listing_id": str(results[0].listing_id)}

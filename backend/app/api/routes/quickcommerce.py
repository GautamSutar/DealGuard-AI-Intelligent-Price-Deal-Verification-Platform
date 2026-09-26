"""
Quick commerce routes — Blinkit, Zepto, Swiggy Instamart, BigBasket Now.

All endpoints require a delivery location (lat/lon).
When omitted, the server uses the configured default location
(QUICKCOMMERCE_DEFAULT_LAT / QUICKCOMMERCE_DEFAULT_LON).

Prices returned are LIVE — they reflect stock and pricing at the
nearest dark store for the given coordinates at query time.
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.config import settings
from app.providers.quickcommerce.quickcommerce_api import (
    QCProduct,
    get_quickcommerce_provider,
)

router = APIRouter()


# ── Response schema ───────────────────────────────────────────────────────────

class QCProductResponse(BaseModel):
    platform: str
    external_id: str
    name: str
    brand: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None
    price: Optional[float] = None
    mrp: Optional[float] = None
    discount_percent: Optional[float] = None
    in_stock: bool = True
    image_url: Optional[str] = None
    url: Optional[str] = None
    delivery_minutes: Optional[int] = None
    observed_at: Optional[str] = None
    source: str = ""

    model_config = {"from_attributes": True}

    @classmethod
    def from_qc(cls, p: QCProduct) -> "QCProductResponse":
        return cls(
            platform=p.platform,
            external_id=p.external_id,
            name=p.name,
            brand=p.brand,
            category=p.category,
            unit=p.unit,
            price=p.price,
            mrp=p.mrp,
            discount_percent=p.discount_percent,
            in_stock=p.in_stock,
            image_url=p.image_url,
            url=p.url,
            delivery_minutes=p.delivery_minutes,
            observed_at=(
                p.observed_at.isoformat() if p.observed_at else None
            ),
            source=p.source,
        )


class QCSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=200)
    platform: Optional[str] = Field(
        None,
        description=(
            "One of: BlinkIt, Zepto, Swiggy Instamart, BigBasket Now. "
            "Omit to search all platforms."
        ),
    )
    lat: Optional[float] = Field(
        None, description="Delivery latitude. Uses server default if omitted."
    )
    lon: Optional[float] = Field(
        None, description="Delivery longitude. Uses server default if omitted."
    )
    limit: int = Field(20, ge=1, le=50)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/quickcommerce/search", response_model=List[QCProductResponse])
async def qc_search(request: QCSearchRequest):
    """
    Search for a product across quick commerce platforms.

    Returns live price and stock data from the nearest dark store
    for the given coordinates.  Results include delivery time per platform.
    """
    lat = request.lat or settings.quickcommerce_default_lat
    lon = request.lon or settings.quickcommerce_default_lon
    provider = get_quickcommerce_provider()
    results = await provider.search(
        query=request.query,
        lat=lat,
        lon=lon,
        platform=request.platform,
        limit=request.limit,
    )
    return [QCProductResponse.from_qc(p) for p in results]


@router.post(
    "/quickcommerce/compare", response_model=List[QCProductResponse]
)
async def qc_compare(request: QCSearchRequest):
    """
    Search all platforms and return results sorted cheapest-first.

    In-stock items come first, out-of-stock items at the end.
    Useful for showing users which platform has the best price
    for a given product right now.
    """
    lat = request.lat or settings.quickcommerce_default_lat
    lon = request.lon or settings.quickcommerce_default_lon
    provider = get_quickcommerce_provider()
    results = await provider.compare_price(
        query=request.query,
        lat=lat,
        lon=lon,
    )
    return [QCProductResponse.from_qc(p) for p in results[:request.limit]]


@router.get(
    "/quickcommerce/item/{platform}/{item_id}",
    response_model=Optional[QCProductResponse],
)
async def qc_item(
    platform: str,
    item_id: str,
    lat: float = Query(
        default=...,
        description="Delivery latitude",
    ),
    lon: float = Query(
        default=...,
        description="Delivery longitude",
    ),
):
    """
    Get a single item by platform and item ID.

    Returns current price, stock status, and delivery estimate
    for the given delivery coordinates.
    """
    provider = get_quickcommerce_provider()
    result = await provider.get_item(item_id, platform, lat, lon)
    if not result:
        return None
    return QCProductResponse.from_qc(result)


@router.get("/quickcommerce/platforms")
async def qc_platforms():
    """List of quick commerce platforms supported by this instance."""
    provider = get_quickcommerce_provider()
    return {
        "platforms": provider.supported_platforms,
        "default_lat": settings.quickcommerce_default_lat,
        "default_lon": settings.quickcommerce_default_lon,
    }

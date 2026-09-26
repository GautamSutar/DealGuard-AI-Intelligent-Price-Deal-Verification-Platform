"""
QuickCommerceAPI provider — api.quickcommerceapi.com

Auth   : X-API-Key header  (or api_key query param)
Key    : stored in QUICKCOMMERCE_API_KEY env var (never committed)
Cost   : 1 credit per call

Endpoints:
  GET /v1/search  — search products by keyword, platform, lat, lon
  GET /v1/item    — single product detail by id + platform + lat/lon

Supported platforms (pass exact string to platform= param):
  BlinkIt | Zepto | Swiggy Instamart | BigBasket Now

Example:
  GET /v1/search?q=milk&platform=BlinkIt&lat=12.90&lon=77.66
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import List, Optional

import httpx
import structlog

from app.config import settings
from app.providers.quickcommerce.base import QCProduct, QuickCommerceProvider

logger = structlog.get_logger(__name__)

# Canonical platform identifiers used in the QuickCommerceAPI query param
PLATFORMS = ["BlinkIt", "Zepto", "Swiggy Instamart", "BigBasket Now"]

# Internal → display name mapping
_PLATFORM_SLUG = {
    "blinkit": "BlinkIt",
    "zepto": "Zepto",
    "swiggy_instamart": "Swiggy Instamart",
    "swiggy": "Swiggy Instamart",
    "bigbasket_now": "BigBasket Now",
    "bigbasket": "BigBasket Now",
}


class QuickCommerceAPIProvider(QuickCommerceProvider):
    """
    Live quick commerce data via api.quickcommerceapi.com.
    One API key covers all platforms.  1 credit per request.
    """

    BASE_URL = "https://api.quickcommerceapi.com"

    def __init__(self):
        self._key = settings.quickcommerce_api_key
        self._headers = {"X-API-Key": self._key}
        self._timeout = httpx.Timeout(20.0)

    @property
    def supported_platforms(self) -> List[str]:
        return list(PLATFORMS)

    # ── Public interface ─────────────────────────────────────────────────────

    async def search(
        self,
        query: str,
        lat: float,
        lon: float,
        platform: Optional[str] = None,
        limit: int = 20,
    ) -> List[QCProduct]:
        """
        GET /v1/search
        Params: q, platform, lat, lon
        If platform is None, fans out to all supported platforms
        concurrently and merges results.
        """
        if platform:
            api_platform = _normalise_platform(platform)
            raw = await self._get("/v1/search", {
                "q": query,
                "platform": api_platform,
                "lat": lat,
                "lon": lon,
            })
            results = _extract_list(raw)
            return [
                _parse_item(r, api_platform, lat, lon)
                for r in results[:limit]
                if r
            ]

        # Fan out to all platforms concurrently
        tasks = [
            self._get("/v1/search", {
                "q": query,
                "platform": p,
                "lat": lat,
                "lon": lon,
            })
            for p in PLATFORMS
        ]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        all_products: List[QCProduct] = []
        for platform_name, raw in zip(PLATFORMS, responses):
            if isinstance(raw, Exception) or not raw:
                continue
            items = _extract_list(raw)
            for r in items[:limit // len(PLATFORMS) + 1]:
                p = _parse_item(r, platform_name, lat, lon)
                if p:
                    all_products.append(p)

        logger.info(
            "QC search complete",
            query=query,
            total=len(all_products),
        )
        return all_products[:limit]

    async def get_item(
        self,
        item_id: str,
        platform: str,
        lat: float,
        lon: float,
    ) -> Optional[QCProduct]:
        """
        GET /v1/item
        Params: id (or item_id), platform, lat, lon
        """
        api_platform = _normalise_platform(platform)
        logger.info(
            "QC item detail",
            item_id=item_id,
            platform=api_platform,
        )
        raw = await self._get("/v1/item", {
            "id": item_id,
            "platform": api_platform,
            "lat": lat,
            "lon": lon,
        })
        if not raw:
            return None
        # /v1/item returns a single object, not a list
        data = raw if isinstance(raw, dict) else {}
        return _parse_item(data, api_platform, lat, lon)

    async def compare_price(
        self,
        query: str,
        lat: float,
        lon: float,
    ) -> List[QCProduct]:
        """
        Search all platforms and return all results sorted by price
        (cheapest first, out-of-stock last).
        """
        all_products = await self.search(
            query, lat, lon, platform=None, limit=40
        )
        in_stock = [p for p in all_products if p.in_stock]
        out_of_stock = [p for p in all_products if not p.in_stock]
        in_stock.sort(key=lambda p: p.price or float("inf"))
        return in_stock + out_of_stock

    # ── HTTP helper ──────────────────────────────────────────────────────────

    async def _get(self, path: str, params: dict) -> Optional[object]:
        url = f"{self.BASE_URL}{path}"
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout
            ) as client:
                resp = await client.get(
                    url, headers=self._headers, params=params
                )
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "QC API HTTP error",
                status=exc.response.status_code,
                endpoint=path,
                body=exc.response.text[:200],
            )
            return None
        except httpx.TimeoutException:
            logger.error("QC API timeout", endpoint=path)
            return None
        except Exception as exc:
            logger.error(
                "QC API request failed",
                error=str(exc),
                endpoint=path,
            )
            return None


# ── Mock provider for development ────────────────────────────────────────────

class QuickCommerceMockProvider(QuickCommerceProvider):
    """Synthetic data — no API key needed for local development."""

    MOCK_DATA = [
        {
            "platform": "BlinkIt",
            "id": "BL_AMUL_MILK_500",
            "name": "Amul Taaza Toned Milk",
            "brand": "Amul",
            "unit": "500 ml",
            "price": 28.0,
            "mrp": 30.0,
            "in_stock": True,
            "category": "Dairy",
            "delivery_minutes": 10,
        },
        {
            "platform": "Zepto",
            "id": "ZP_AMUL_MILK_500",
            "name": "Amul Taaza Toned Milk",
            "brand": "Amul",
            "unit": "500 ml",
            "price": 27.0,
            "mrp": 30.0,
            "in_stock": True,
            "category": "Dairy",
            "delivery_minutes": 8,
        },
        {
            "platform": "Swiggy Instamart",
            "id": "SI_AMUL_MILK_500",
            "name": "Amul Taaza Toned Milk",
            "brand": "Amul",
            "unit": "500 ml",
            "price": 29.0,
            "mrp": 30.0,
            "in_stock": False,
            "category": "Dairy",
            "delivery_minutes": 15,
        },
    ]

    @property
    def supported_platforms(self) -> List[str]:
        return list(PLATFORMS)

    async def search(
        self,
        query: str,
        lat: float,
        lon: float,
        platform: Optional[str] = None,
        limit: int = 20,
    ) -> List[QCProduct]:
        results = []
        q = query.lower()
        for row in self.MOCK_DATA:
            if any(w in row["name"].lower() for w in q.split()):
                if platform and row["platform"].lower() != platform.lower():
                    continue
                results.append(_mock_to_product(row, lat, lon))
        if not results:
            results = [
                _mock_to_product(self.MOCK_DATA[0], lat, lon)
            ]
        return results[:limit]

    async def get_item(
        self,
        item_id: str,
        platform: str,
        lat: float,
        lon: float,
    ) -> Optional[QCProduct]:
        for row in self.MOCK_DATA:
            if row["id"] == item_id:
                return _mock_to_product(row, lat, lon)
        return None

    async def compare_price(
        self,
        query: str,
        lat: float,
        lon: float,
    ) -> List[QCProduct]:
        results = await self.search(query, lat, lon, limit=40)
        in_stock = sorted(
            [p for p in results if p.in_stock],
            key=lambda p: p.price or float("inf"),
        )
        out_of_stock = [p for p in results if not p.in_stock]
        return in_stock + out_of_stock


# ── Factory ───────────────────────────────────────────────────────────────────

def get_quickcommerce_provider() -> QuickCommerceProvider:
    if settings.quickcommerce_api_key:
        logger.info("Using QuickCommerceAPI live provider")
        return QuickCommerceAPIProvider()
    logger.warning(
        "QUICKCOMMERCE_API_KEY not set — using mock QC provider"
    )
    return QuickCommerceMockProvider()


# ── Standalone helpers ────────────────────────────────────────────────────────

def _normalise_platform(name: str) -> str:
    """Map user-supplied platform name to the API's expected string."""
    return _PLATFORM_SLUG.get(name.lower().replace(" ", "_"), name)


def _extract_list(raw) -> list:
    """Extract items list from varied response shapes."""
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        for key in ("results", "products", "items", "data"):
            val = raw.get(key)
            if isinstance(val, list):
                return val
    return []


def _parse_item(
    data: dict, platform: str, lat: float, lon: float
) -> Optional[QCProduct]:
    """Parse a single item dict from QuickCommerceAPI response."""
    if not isinstance(data, dict):
        return None

    name = (
        data.get("name")
        or data.get("product_name")
        or data.get("title")
    )
    if not name:
        return None

    price = _to_float(
        data.get("price")
        or data.get("selling_price")
        or data.get("sp")
    )
    mrp = _to_float(
        data.get("mrp")
        or data.get("market_price")
        or data.get("original_price")
    )
    discount_pct = _to_float(
        data.get("discount_percent")
        or data.get("discount")
    )

    # Infer discount if not provided
    if not discount_pct and price and mrp and mrp > price:
        discount_pct = round((mrp - price) / mrp * 100, 1)

    item_id = str(
        data.get("id")
        or data.get("item_id")
        or data.get("sku_id")
        or ""
    )
    in_stock = bool(
        data.get("in_stock", True)
        or data.get("available", True)
        or data.get("is_available", True)
    )
    # Explicit out-of-stock overrides
    if data.get("in_stock") is False or data.get("available") is False:
        in_stock = False

    return QCProduct(
        platform=platform,
        external_id=item_id,
        name=name,
        brand=data.get("brand"),
        category=data.get("category"),
        unit=data.get("unit") or data.get("quantity"),
        price=price,
        mrp=mrp,
        discount_percent=discount_pct,
        in_stock=in_stock,
        image_url=data.get("image") or data.get("image_url"),
        url=data.get("url") or data.get("deep_link"),
        delivery_minutes=_to_int(data.get("delivery_time_minutes")),
        lat=lat,
        lon=lon,
        observed_at=datetime.now(timezone.utc),
        source=f"quickcommerceapi/{platform.lower().replace(' ', '_')}",
        confidence=1.0,
    )


def _mock_to_product(row: dict, lat: float, lon: float) -> QCProduct:
    return QCProduct(
        platform=row["platform"],
        external_id=row["id"],
        name=row["name"],
        brand=row.get("brand"),
        category=row.get("category"),
        unit=row.get("unit"),
        price=row.get("price"),
        mrp=row.get("mrp"),
        in_stock=row.get("in_stock", True),
        delivery_minutes=row.get("delivery_minutes"),
        lat=lat,
        lon=lon,
        observed_at=datetime.now(timezone.utc),
        source="mock/quickcommerce",
        confidence=1.0,
    )


def _to_float(val) -> Optional[float]:
    if val is None:
        return None
    try:
        f = float(val)
        return round(f, 2) if f > 0 else None
    except (TypeError, ValueError):
        return None


def _to_int(val) -> Optional[int]:
    if val is None:
        return None
    try:
        return int(val)
    except (TypeError, ValueError):
        return None

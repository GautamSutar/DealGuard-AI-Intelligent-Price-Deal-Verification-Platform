"""
RapidAPI Amazon provider — real live data, no scraping.

Supports the following RapidAPI Amazon data services (same endpoint structure):
  - Real-Time Amazon Data   : real-time-amazon-data.p.rapidapi.com
  - Amazon Product Data     : amazon-product-data6.p.rapidapi.com
  - Axesso Amazon           : axesso-amazon-data-service.p.rapidapi.com

Configure via environment:
  AMAZON_PROVIDER=rapidapi
  RAPIDAPI_KEY=520c1b436d836db9f48821e9dc0a2b0d
  RAPIDAPI_AMAZON_HOST=real-time-amazon-data.p.rapidapi.com
  RAPIDAPI_AMAZON_COUNTRY=IN
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import List, Optional

import httpx
import structlog

from app.config import settings
from app.providers.marketplace.amazon.amazon_parser import parse_asin_from_url
from app.providers.marketplace.base import MarketplaceProvider, ProviderOffer, ProviderProduct

logger = structlog.get_logger(__name__)


class RapidAPIAmazonProvider(MarketplaceProvider):
    """
    Calls the RapidAPI Amazon product data service.
    All data comes from RapidAPI — never fabricated.
    """

    def __init__(self):
        self._key = settings.rapidapi_key
        self._host = settings.rapidapi_amazon_host
        self._country = settings.rapidapi_amazon_country
        self._base_url = f"https://{self._host}"
        self._headers = {
            "X-RapidAPI-Key": self._key,
            "X-RapidAPI-Host": self._host,
        }
        self._timeout = httpx.Timeout(15.0)

    @property
    def marketplace_name(self) -> str:
        return "amazon"

    # ── Public interface ─────────────────────────────────────────────────────

    async def search_products(self, query: str, limit: int = 10) -> List[ProviderProduct]:
        logger.info("RapidAPI Amazon: search", query=query)
        data = await self._get("/search", params={
            "query": query,
            "country": self._country,
            "category_id": "aps",
            "page": "1",
        })
        if not data:
            return []
        return self._parse_search_results(data, limit)

    async def get_product(self, external_id: str) -> Optional[ProviderProduct]:
        logger.info("RapidAPI Amazon: get product", asin=external_id)
        data = await self._get("/product-details", params={
            "asin": external_id,
            "country": self._country,
        })
        if not data:
            return None
        return self._parse_product_details(data)

    async def get_current_offers(self, external_id: str) -> List[ProviderOffer]:
        logger.info("RapidAPI Amazon: get offers", asin=external_id)
        data = await self._get("/product-offers", params={
            "asin": external_id,
            "country": self._country,
            "limit": "5",
        })
        if not data:
            return []
        return self._parse_offers(data)

    async def get_product_from_url(self, url: str) -> Optional[ProviderProduct]:
        asin = parse_asin_from_url(url)
        if asin:
            return await self.get_product(asin)
        return None

    # ── HTTP helpers ─────────────────────────────────────────────────────────

    async def _get(self, path: str, params: dict) -> Optional[dict]:
        url = f"{self._base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(url, headers=self._headers, params=params)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as exc:
            logger.error("RapidAPI HTTP error", status=exc.response.status_code, url=url)
            return None
        except Exception as exc:
            logger.error("RapidAPI request failed", error=str(exc), url=url)
            return None

    # ── Response parsers ─────────────────────────────────────────────────────

    def _parse_search_results(self, data: dict, limit: int) -> List[ProviderProduct]:
        products = []
        # Real-Time Amazon Data returns data.products or data.data.products
        items = (
            data.get("products")
            or data.get("data", {}).get("products")
            or data.get("searchResult", {}).get("products")
            or []
        )
        for item in items[:limit]:
            p = self._item_to_provider_product(item)
            if p:
                products.append(p)
        return products

    def _parse_product_details(self, data: dict) -> Optional[ProviderProduct]:
        # Unwrap common wrapper keys
        item = (
            data.get("data")
            or data.get("product")
            or data.get("productDetails")
            or data
        )
        return self._item_to_provider_product(item)

    def _item_to_provider_product(self, item: dict) -> Optional[ProviderProduct]:
        """
        Maps a raw RapidAPI item dict to ProviderProduct.

        Different RapidAPI Amazon services use slightly different field names,
        so we probe multiple keys to stay compatible.
        """
        asin = (
            item.get("asin")
            or item.get("product_id")
            or item.get("ASIN")
        )
        if not asin:
            return None

        title = (
            item.get("product_title")
            or item.get("title")
            or item.get("name")
            or "Unknown Product"
        )

        # Price — try several common field names (all in INR for IN country)
        selling_price = _extract_price(
            item.get("product_price")
            or item.get("price")
            or item.get("currentPrice")
            or item.get("buybox_winner", {}).get("price", {}).get("value")
        )

        mrp = _extract_price(
            item.get("product_original_price")
            or item.get("original_price")
            or item.get("listPrice")
            or item.get("mrp")
        )

        image_url = (
            item.get("product_photo")
            or item.get("image")
            or item.get("main_image", {}).get("link")
            or (item.get("product_photos") or [None])[0]
        )

        url = (
            item.get("product_url")
            or item.get("url")
            or (f"https://www.amazon.in/dp/{asin}" if asin else None)
        )

        brand = (
            item.get("product_brand")
            or item.get("brand")
            or item.get("brandName")
        )

        availability_raw = item.get("product_availability") or item.get("availability") or ""
        availability = "out" not in str(availability_raw).lower()

        # Parse offers if embedded
        raw_offers = item.get("product_information", {}).get("offers", [])
        offers = self._parse_offers_from_list(raw_offers)

        effective_price = self._compute_effective_price(selling_price, offers)

        return ProviderProduct(
            marketplace="amazon",
            external_id=asin,
            title=title,
            url=url,
            brand=brand,
            image_url=image_url,
            mrp=mrp,
            selling_price=selling_price,
            effective_price=effective_price,
            currency="INR",
            availability=availability,
            offers=offers,
            observed_at=datetime.now(timezone.utc),
            source=f"rapidapi:{self._host}",
            confidence=1.0,
        )

    def _parse_offers(self, data: dict) -> List[ProviderOffer]:
        items = (
            data.get("offers")
            or data.get("data", {}).get("offers")
            or []
        )
        return self._parse_offers_from_list(items)

    def _parse_offers_from_list(self, items: list) -> List[ProviderOffer]:
        offers: List[ProviderOffer] = []
        for o in items:
            if not isinstance(o, dict):
                continue
            title = o.get("title") or o.get("description") or o.get("type", "Offer")
            discount_value = _extract_price(o.get("discount") or o.get("discountAmount"))
            discount_pct = _extract_float(o.get("discountPercentage") or o.get("discount_percentage"))

            # Detect bank/card offers (conditional)
            is_conditional = any(
                kw in str(title).lower()
                for kw in ("hdfc", "sbi", "icici", "axis", "kotak", "card", "bank", "emi", "exchange")
            )

            offers.append(ProviderOffer(
                offer_type="bank" if is_conditional else "coupon",
                title=title,
                discount_value=discount_value,
                discount_percentage=discount_pct,
                coupon_code=o.get("couponCode") or o.get("code"),
                eligibility=o.get("eligibility") or o.get("terms"),
                is_conditional=is_conditional,
                source=f"rapidapi:{self._host}",
            ))
        return offers

    def _compute_effective_price(
        self, base: Optional[float], offers: List[ProviderOffer]
    ) -> Optional[float]:
        if base is None:
            return None
        effective = base
        for o in offers:
            if not o.is_conditional and o.offer_type == "coupon" and o.discount_value:
                effective -= o.discount_value
        return round(max(effective, 0), 2)


# ── Utility helpers ──────────────────────────────────────────────────────────

def _extract_price(raw) -> Optional[float]:
    """Parse ₹69,999 / '69999' / 69999.0 / None → float or None."""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return round(float(raw), 2) if raw > 0 else None
    s = str(raw).replace("₹", "").replace(",", "").replace(" ", "").strip()
    s = re.sub(r"[^\d.]", "", s)
    try:
        val = float(s)
        return round(val, 2) if val > 0 else None
    except ValueError:
        return None


def _extract_float(raw) -> Optional[float]:
    if raw is None:
        return None
    try:
        return float(str(raw).replace("%", "").strip())
    except ValueError:
        return None

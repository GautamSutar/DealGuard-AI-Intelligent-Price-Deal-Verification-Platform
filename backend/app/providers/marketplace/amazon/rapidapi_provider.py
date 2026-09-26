"""
Real-Time Amazon Data provider via RapidAPI.

Host   : real-time-amazon-data.p.rapidapi.com
Docs   : https://rapidapi.com/real-time-amazon-data/api/real-time-amazon-data

Endpoints used:
  GET /search           — Product Search
  GET /product-details  — Product Details  (asin + country)
  GET /product-offers   — Product Offers   (asin + country)
  GET /url-product      — Scrape By URL    (url)

Configure via environment:
  AMAZON_PROVIDER=rapidapi
  RAPIDAPI_KEY=<your key>
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
from app.providers.marketplace.base import MarketplaceProvider, ProviderOffer, ProviderProduct

logger = structlog.get_logger(__name__)


class RealTimeAmazonProvider(MarketplaceProvider):
    """
    Production provider backed by real-time-amazon-data.p.rapidapi.com.
    Returns live Amazon IN data — no mock, no fabrication.
    """

    BASE_URL = "https://real-time-amazon-data.p.rapidapi.com"

    def __init__(self):
        self._key = settings.rapidapi_key
        self._host = settings.rapidapi_amazon_host
        self._country = settings.rapidapi_amazon_country
        self._headers = {
            "X-RapidAPI-Key": self._key,
            "X-RapidAPI-Host": self._host,
        }
        self._timeout = httpx.Timeout(20.0)

    @property
    def marketplace_name(self) -> str:
        return "amazon"

    # ── Public interface ─────────────────────────────────────────────────────

    async def search_products(self, query: str, limit: int = 10) -> List[ProviderProduct]:
        """
        GET /search
        Params: query, country, page, sort_by
        Response: data.products[]
        """
        logger.info("RealTimeAmazon: search", query=query, country=self._country)
        raw = await self._get("/search", {
            "query": query,
            "country": self._country,
            "page": "1",
            "sort_by": "RELEVANCE",
        })
        if not raw or raw.get("status") != "OK":
            logger.warning("Search returned no OK status", response=raw)
            return []

        items = raw.get("data", {}).get("products", [])
        products = []
        for item in items[:limit]:
            p = self._parse_search_item(item)
            if p:
                products.append(p)
        logger.info("Search complete", results=len(products))
        return products

    async def get_product(self, external_id: str) -> Optional[ProviderProduct]:
        """
        GET /product-details
        Params: asin, country, autoselect_variant=true
        Response: data (single product object)
        """
        logger.info("RealTimeAmazon: product details", asin=external_id)
        raw = await self._get("/product-details", {
            "asin": external_id,
            "country": self._country,
            "autoselect_variant": "true",
        })
        if not raw or raw.get("status") != "OK":
            logger.warning("Product details returned no data", asin=external_id)
            return None

        data = raw.get("data", {})
        return self._parse_product_detail(data, external_id)

    async def get_current_offers(self, external_id: str) -> List[ProviderOffer]:
        """
        GET /product-offers
        Params: asin, country, limit
        Response: data.offers[]
        Each offer has price_info and seller_info.
        """
        logger.info("RealTimeAmazon: product offers", asin=external_id)
        raw = await self._get("/product-offers", {
            "asin": external_id,
            "country": self._country,
            "limit": "5",
        })
        if not raw or raw.get("status") != "OK":
            return []

        offers_raw = raw.get("data", {}).get("offers", [])
        return self._parse_offers(offers_raw)

    async def get_product_from_url(self, url: str) -> Optional[ProviderProduct]:
        """
        GET /url-product (Scrape By URL endpoint)
        Falls back to ASIN extraction if URL parsing fails.
        """
        logger.info("RealTimeAmazon: scrape by URL", url=url)
        raw = await self._get("/url-product", {
            "url": url,
            "country": self._country,
        })
        if raw and raw.get("status") == "OK":
            data = raw.get("data", {})
            asin = data.get("asin")
            if asin:
                return self._parse_product_detail(data, asin)

        # Fallback: extract ASIN from URL and call product-details
        asin = _extract_asin_from_url(url)
        if asin:
            return await self.get_product(asin)

        logger.warning("Could not resolve product from URL", url=url)
        return None

    # ── HTTP helper ──────────────────────────────────────────────────────────

    async def _get(self, path: str, params: dict) -> Optional[dict]:
        url = f"{self.BASE_URL}{path}"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(url, headers=self._headers, params=params)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "RapidAPI HTTP error",
                status=exc.response.status_code,
                endpoint=path,
                body=exc.response.text[:200],
            )
            return None
        except httpx.TimeoutException:
            logger.error("RapidAPI timeout", endpoint=path)
            return None
        except Exception as exc:
            logger.error("RapidAPI request failed", error=str(exc), endpoint=path)
            return None

    # ── Response parsers ─────────────────────────────────────────────────────

    def _parse_search_item(self, item: dict) -> Optional[ProviderProduct]:
        """
        Search result item fields (real-time-amazon-data search response):
          asin, product_title, product_price, product_original_price,
          currency, product_url, product_photo, is_best_seller,
          product_minimum_offer_price, is_prime, sales_volume
        """
        asin = item.get("asin")
        if not asin:
            return None

        title = item.get("product_title", "Unknown Product")
        selling_price = _parse_price(item.get("product_price"))
        mrp = _parse_price(item.get("product_original_price"))
        image = item.get("product_photo")
        url = item.get("product_url") or f"https://www.amazon.in/dp/{asin}"
        availability = "out" not in str(item.get("product_availability", "")).lower()

        # minimum_offer_price is sometimes the effective after-coupon price
        min_offer = _parse_price(item.get("product_minimum_offer_price"))
        effective = min_offer if (min_offer and selling_price and min_offer < selling_price) \
            else selling_price

        return ProviderProduct(
            marketplace="amazon",
            external_id=asin,
            title=title,
            url=url,
            brand=None,  # not in search results; fetched on product-details
            image_url=image,
            mrp=mrp,
            selling_price=selling_price,
            effective_price=effective,
            currency="INR",
            availability=availability,
            offers=[],
            observed_at=datetime.now(timezone.utc),
            source="real-time-amazon-data/search",
            confidence=1.0,
        )

    def _parse_product_detail(self, data: dict, asin: str) -> Optional[ProviderProduct]:
        """
        Product details fields:
          asin, product_title, product_price, product_original_price,
          currency, product_availability, product_photo, product_photos,
          product_url, product_information, about_product, product_details,
          product_star_rating, product_num_ratings, product_num_offers,
          product_minimum_offer_price, is_best_seller, is_amazon_choice,
          is_prime, has_variations, product_variations
        """
        title = data.get("product_title", "Unknown Product")
        selling_price = _parse_price(data.get("product_price"))
        mrp = _parse_price(data.get("product_original_price"))

        # Extract brand from product_information or about_product
        brand = self._extract_brand(data)

        # Best image
        image = (
            data.get("product_photo")
            or (data.get("product_photos") or [None])[0]
        )
        url = data.get("product_url") or f"https://www.amazon.in/dp/{asin}"

        availability_text = data.get("product_availability", "In Stock")
        availability = "out of stock" not in str(availability_text).lower()

        min_offer = _parse_price(data.get("product_minimum_offer_price"))
        effective = min_offer if (min_offer and selling_price and min_offer < selling_price) \
            else selling_price

        return ProviderProduct(
            marketplace="amazon",
            external_id=asin,
            title=title,
            url=url,
            brand=brand,
            variant=self._extract_variant(data),
            image_url=image,
            mrp=mrp,
            selling_price=selling_price,
            effective_price=effective,
            currency="INR",
            availability=availability,
            offers=[],  # call get_current_offers separately
            observed_at=datetime.now(timezone.utc),
            source="real-time-amazon-data/product-details",
            confidence=1.0,
        )

    def _parse_offers(self, raw_offers: list) -> List[ProviderOffer]:
        """
        Offer structure from /product-offers:
          offer_id, condition, seller_info.seller_name,
          price_info.price / price_info.raw_price / price_info.currency,
          is_buybox_winner, is_prime, delivery_info
        """
        result: List[ProviderOffer] = []
        for o in raw_offers:
            price_info = o.get("price_info", {})
            seller_info = o.get("seller_info", {})
            seller_name = seller_info.get("seller_name", "")

            price = (
                _parse_price(price_info.get("raw_price"))
                or price_info.get("price")
            )
            if not price:
                continue

            result.append(ProviderOffer(
                offer_type="seller",
                title=f"Sold by {seller_name}" if seller_name else "Marketplace offer",
                discount_value=None,
                is_conditional=False,
                source="real-time-amazon-data/product-offers",
            ))
        return result

    # ── Field extraction helpers ─────────────────────────────────────────────

    def _extract_brand(self, data: dict) -> Optional[str]:
        """Try product_information.brand or product_details.Brand."""
        info = data.get("product_information", {})
        if isinstance(info, dict):
            brand = info.get("brand") or info.get("Brand") or info.get("manufacturer")
            if brand:
                return str(brand).strip()
        details = data.get("product_details", {})
        if isinstance(details, dict):
            brand = details.get("Brand") or details.get("brand")
            if brand:
                return str(brand).strip()
        return None

    def _extract_variant(self, data: dict) -> Optional[str]:
        """Try to extract variant string from product variations or title."""
        variations = data.get("product_variations", {})
        if isinstance(variations, dict):
            parts = []
            for key, val in variations.items():
                if isinstance(val, str):
                    parts.append(val)
                elif isinstance(val, dict):
                    selected = val.get("selected") or val.get("value")
                    if selected:
                        parts.append(str(selected))
            if parts:
                return " / ".join(parts)
        return None


# ── Standalone helpers ────────────────────────────────────────────────────────

def _parse_price(raw) -> Optional[float]:
    """
    Normalise any price representation to a float in INR.
    Handles: '₹69,999', '69999.0', 69999, None, '$0'
    """
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return round(float(raw), 2) if float(raw) > 0 else None
    # Strip currency symbols, commas, spaces
    cleaned = re.sub(r"[₹$£€,\s]", "", str(raw)).strip()
    # Keep only digits and decimal point
    cleaned = re.sub(r"[^\d.]", "", cleaned)
    try:
        val = float(cleaned)
        return round(val, 2) if val > 0 else None
    except ValueError:
        return None


def _extract_asin_from_url(url: str) -> Optional[str]:
    """Extract B0XXXXXXXXXX ASIN from any Amazon URL format."""
    match = re.search(r"/(?:dp|gp/product)/([A-Z0-9]{10})", url)
    return match.group(1) if match else None

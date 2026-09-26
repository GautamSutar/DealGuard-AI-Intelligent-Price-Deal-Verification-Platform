"""
Flipkart provider via ReefAPI.

Host   : api.reefapi.com
Docs   : https://reefapi.com/docs (flipkart section)

Endpoints used (all POST, JSON body, x-api-key header):
  POST /flipkart/v1/search   — product search
  POST /flipkart/v1/product  — full product detail
  POST /flipkart/v1/offers   — bank/exchange/coupon offers
  POST /flipkart/v1/similar  — (future use)

Each call costs 1 credit.  Offers call is separate (+1 credit).

Configure via environment:
  FLIPKART_PROVIDER=reefapi
  REEFAPI_KEY=<your key>

Response envelope:
  { "ok": bool, "data": {...}, "meta": {...}, "error": {...} }
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import List, Optional

import httpx
import structlog

from app.config import settings
from app.providers.marketplace.base import (
    MarketplaceProvider,
    ProviderOffer,
    ProviderProduct,
)

logger = structlog.get_logger(__name__)

# Offer types that require a specific bank card / exchange — never
# auto-subtract from base price; stored as is_conditional=True.
_CONDITIONAL_OFFER_KEYWORDS = frozenset([
    "bank", "card", "hdfc", "sbi", "icici", "axis", "kotak",
    "exchange", "emi", "no cost emi", "cashback", "wallet",
])


class ReefAPIFlipkartProvider(MarketplaceProvider):
    """
    Production provider backed by ReefAPI /flipkart endpoints.
    Returns live Flipkart India data — no mock, no fabrication.
    """

    BASE_URL = "https://api.reefapi.com"

    def __init__(self):
        self._key = settings.reefapi_key
        self._headers = {
            "x-api-key": self._key,
            "content-type": "application/json",
        }
        self._timeout = httpx.Timeout(25.0)

    @property
    def marketplace_name(self) -> str:
        return "flipkart"

    # ── Public interface ─────────────────────────────────────────────────────

    async def search_products(
        self, query: str, limit: int = 10
    ) -> List[ProviderProduct]:
        """
        POST /flipkart/v1/search
        Body: { q, page }
        Response: data.results[]
        """
        logger.info("ReefAPI Flipkart: search", query=query)
        raw = await self._post("/flipkart/v1/search", {
            "q": query,
            "page": 1,
        })
        if not raw:
            return []

        results = raw.get("results", [])
        products = []
        for item in results[:limit]:
            p = self._parse_search_item(item)
            if p:
                products.append(p)

        logger.info("Flipkart search complete", results=len(products))
        return products

    async def get_product(self, external_id: str) -> Optional[ProviderProduct]:
        """
        POST /flipkart/v1/product
        Body: { itm_id }  — or { url }
        Response: data (single product)
        """
        logger.info("ReefAPI Flipkart: product detail", itm_id=external_id)
        raw = await self._post("/flipkart/v1/product", {
            "itm_id": external_id,
        })
        if not raw:
            return None
        return self._parse_product_detail(raw, external_id)

    async def get_current_offers(
        self, external_id: str
    ) -> List[ProviderOffer]:
        """
        POST /flipkart/v1/offers
        Body: { itm_id }
        Response: data — list of typed offer rows
        """
        logger.info(
            "ReefAPI Flipkart: offers", itm_id=external_id
        )
        raw = await self._post("/flipkart/v1/offers", {
            "itm_id": external_id,
        })
        if not raw:
            return []
        # data may be a list or a dict with an offers key
        if isinstance(raw, list):
            return self._parse_offers(raw)
        if isinstance(raw, dict):
            offers_list = (
                raw.get("offers")
                or raw.get("offer_list")
                or []
            )
            return self._parse_offers(offers_list)
        return []

    async def get_product_from_url(
        self, url: str
    ) -> Optional[ProviderProduct]:
        """
        POST /flipkart/v1/product  with url param.
        Falls back to extracting itm_id from the URL.
        """
        logger.info("ReefAPI Flipkart: product from URL", url=url)
        raw = await self._post("/flipkart/v1/product", {"url": url})
        if raw:
            itm_id = _extract_itm_id_from_url(url)
            return self._parse_product_detail(raw, itm_id or "unknown")

        # Fallback: extract itm_id and retry
        itm_id = _extract_itm_id_from_url(url)
        if itm_id:
            return await self.get_product(itm_id)

        logger.warning(
            "Could not resolve Flipkart product from URL", url=url
        )
        return None

    # ── HTTP helper ──────────────────────────────────────────────────────────

    async def _post(
        self, path: str, body: dict
    ) -> Optional[dict]:
        """
        POST to ReefAPI.  Returns data dict on ok:true, None on any error.
        """
        url = f"{self.BASE_URL}{path}"
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout
            ) as client:
                resp = await client.post(
                    url, headers=self._headers, json=body
                )
                resp.raise_for_status()
                envelope = resp.json()

            if not envelope.get("ok"):
                err = envelope.get("error") or {}
                logger.warning(
                    "ReefAPI error",
                    code=err.get("code"),
                    message=err.get("message"),
                    endpoint=path,
                )
                return None

            return envelope.get("data")

        except httpx.HTTPStatusError as exc:
            logger.error(
                "ReefAPI HTTP error",
                status=exc.response.status_code,
                endpoint=path,
                body=exc.response.text[:200],
            )
            return None
        except httpx.TimeoutException:
            logger.error("ReefAPI timeout", endpoint=path)
            return None
        except Exception as exc:
            logger.error(
                "ReefAPI request failed",
                error=str(exc),
                endpoint=path,
            )
            return None

    # ── Response parsers ─────────────────────────────────────────────────────

    def _parse_search_item(self, item: dict) -> Optional[ProviderProduct]:
        """
        Search result fields (ReefAPI /flipkart/v1/search):
          product_id, listing_id, itm_id, title, url,
          price, mrp, discount_percent, currency,
          rating, rating_count, image, in_stock, key_specs,
          flipkart_advantage
        """
        itm_id = item.get("itm_id") or item.get("product_id")
        if not itm_id:
            return None

        title = item.get("title", "Unknown Product")
        selling_price = _to_float(item.get("price"))
        mrp = _to_float(item.get("mrp"))
        image = item.get("image") or (item.get("images") or [None])[0]
        url = item.get("url", "")
        in_stock = bool(item.get("in_stock", True))

        return ProviderProduct(
            marketplace="flipkart",
            external_id=itm_id,
            title=title,
            url=url,
            brand=None,  # not in search results
            image_url=image,
            mrp=mrp,
            selling_price=selling_price,
            effective_price=selling_price,  # refined by offers call
            currency="INR",
            availability=in_stock,
            offers=[],
            observed_at=datetime.now(timezone.utc),
            source="reefapi/flipkart/search",
            confidence=1.0,
        )

    def _parse_product_detail(
        self, data: dict, itm_id: str
    ) -> Optional[ProviderProduct]:
        """
        Full product fields (ReefAPI /flipkart/v1/product):
          title, price, mrp, url, image/images,
          brand, rating, in_stock, availability,
          seller (dict), specs, highlights, product_id, itm_id
        """
        title = data.get("title", "Unknown Product")
        selling_price = _to_float(data.get("price"))
        mrp = _to_float(data.get("mrp"))

        image = data.get("image") or (
            (data.get("images") or [None])[0]
        )
        url = data.get("url", "")
        in_stock = bool(data.get("in_stock", True))

        # Brand is sometimes inside seller dict or a top-level brand key
        seller = data.get("seller") or {}
        brand = data.get("brand") or seller.get("brand")

        real_itm = (
            data.get("itm_id")
            or data.get("product_id")
            or itm_id
        )

        return ProviderProduct(
            marketplace="flipkart",
            external_id=real_itm,
            title=title,
            url=url,
            brand=brand,
            image_url=image,
            mrp=mrp,
            selling_price=selling_price,
            effective_price=selling_price,
            currency="INR",
            availability=in_stock,
            offers=[],  # populated via get_current_offers
            observed_at=datetime.now(timezone.utc),
            source="reefapi/flipkart/product",
            confidence=1.0,
        )

    def _parse_offers(self, raw_offers: list) -> List[ProviderOffer]:
        """
        Offer rows from ReefAPI /flipkart/v1/offers.
        Each row carries: type, title/label, amount/value,
        and optionally bank/card info.

        Key Flipkart offer types:
          deal      — direct discount (unconditional)
          coupon    — apply-at-checkout (unconditional)
          bank      — requires specific card (conditional)
          exchange  — requires trade-in device (conditional)
          cashback  — wallet cashback (conditional)
          emi       — no-cost EMI plan (informational)
        """
        result: List[ProviderOffer] = []
        for o in raw_offers:
            if not isinstance(o, dict):
                continue

            offer_type = str(
                o.get("type") or o.get("offer_type") or "deal"
            ).lower()
            title = str(
                o.get("title") or o.get("label") or o.get("text") or ""
            )
            amount = _to_float(
                o.get("amount") or o.get("value") or o.get("discount")
            )

            is_conditional = _is_conditional_offer(offer_type, title)

            result.append(ProviderOffer(
                offer_type=offer_type,
                title=title,
                discount_value=amount,
                is_conditional=is_conditional,
                eligibility=o.get("eligibility") or o.get("bank"),
                source="reefapi/flipkart/offers",
            ))

        return result


# ── Standalone helpers ────────────────────────────────────────────────────────

def _is_conditional_offer(offer_type: str, title: str) -> bool:
    """
    Bank/exchange/EMI/wallet offers require specific conditions.
    A search on type and title catches both ReefAPI-typed rows and
    free-text rows that mention a bank name.
    """
    combined = f"{offer_type} {title}".lower()
    return any(kw in combined for kw in _CONDITIONAL_OFFER_KEYWORDS)


def _to_float(raw) -> Optional[float]:
    """Convert price values to float; returns None on failure/zero."""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return round(float(raw), 2) if float(raw) > 0 else None
    cleaned = re.sub(r"[₹,\s]", "", str(raw))
    cleaned = re.sub(r"[^\d.]", "", cleaned)
    try:
        val = float(cleaned)
        return round(val, 2) if val > 0 else None
    except ValueError:
        return None


def _extract_itm_id_from_url(url: str) -> Optional[str]:
    """
    Extract the itm_id from a Flipkart product URL.
    URL format: /p/<itm_id>?pid=<FSN>
    itm pattern: itm[0-9a-f]{13}
    """
    match = re.search(r"(itm[0-9a-f]{13})", url)
    return match.group(1) if match else None

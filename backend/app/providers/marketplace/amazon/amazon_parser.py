"""Parses raw Amazon provider data into normalised ProviderProduct."""

import re
from datetime import datetime, timezone
from typing import List, Optional

from app.providers.marketplace.amazon.amazon_models import AmazonRawProduct, AmazonRawOffer
from app.providers.marketplace.base import ProviderOffer, ProviderProduct


def parse_asin_from_url(url: str) -> Optional[str]:
    """Extract ASIN from a standard Amazon product URL."""
    pattern = r"/(?:dp|gp/product)/([A-Z0-9]{10})"
    match = re.search(pattern, url)
    return match.group(1) if match else None


def parse_amazon_product(raw: AmazonRawProduct, source: str = "amazon") -> ProviderProduct:
    offers = [_parse_offer(o) for o in raw.raw_offers]
    effective_price = _calculate_effective_price(raw.price, offers)

    return ProviderProduct(
        marketplace="amazon",
        external_id=raw.asin,
        title=raw.title,
        url=raw.url,
        brand=raw.brand,
        variant=raw.variant,
        image_url=raw.image_url,
        mrp=raw.mrp,
        selling_price=raw.price,
        effective_price=effective_price,
        currency=raw.currency,
        seller_name=raw.seller_name,
        availability=raw.availability,
        offers=offers,
        observed_at=datetime.now(timezone.utc),
        source=source,
        confidence=1.0,
    )


def _parse_offer(raw: dict) -> ProviderOffer:
    return ProviderOffer(
        offer_type=raw.get("type", "coupon"),
        title=raw.get("title", ""),
        discount_value=raw.get("discount_value"),
        discount_percentage=raw.get("discount_percentage"),
        coupon_code=raw.get("coupon_code"),
        eligibility=raw.get("eligibility"),
        conditions=raw.get("conditions"),
        is_conditional=raw.get("is_conditional", False),
        source="amazon",
    )


def _calculate_effective_price(base: Optional[float], offers: List[ProviderOffer]) -> Optional[float]:
    """
    Only subtract UNCONDITIONAL offers (coupons with no eligibility requirement).
    Bank offers, card-specific deals etc. are conditional and must NOT be subtracted.
    """
    if base is None:
        return None
    effective = base
    for offer in offers:
        if not offer.is_conditional and offer.offer_type == "coupon" and offer.discount_value:
            effective -= offer.discount_value
    return round(max(effective, 0), 2)

"""
Normalises product titles from different marketplaces into canonical attributes.

Uses deterministic rules first. LLM matching (for ambiguous cases) is a future
enhancement and must return a confidence score if implemented.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class NormalisedProduct:
    canonical_name: str
    brand: Optional[str] = None
    model: Optional[str] = None
    storage: Optional[str] = None
    ram: Optional[str] = None
    color: Optional[str] = None
    size: Optional[str] = None
    variant_description: Optional[str] = None
    confidence: float = 1.0


_STORAGE_PATTERN = re.compile(r"\b(\d+)\s*(GB|TB)\b", re.IGNORECASE)
_RAM_PATTERN = re.compile(r"\b(\d+)\s*GB\s*RAM\b", re.IGNORECASE)
_SIZE_PATTERN = re.compile(r"\b(\d+(?:\.\d+)?)\s*(inch(?:es)?|\")\b", re.IGNORECASE)

_KNOWN_BRANDS = [
    "Apple", "Samsung", "Sony", "OnePlus", "Realme", "Xiaomi", "Redmi",
    "OPPO", "Vivo", "Nokia", "Motorola", "LG", "Philips", "Bosch",
    "Whirlpool", "Haier", "Voltas", "Daikin", "Noise", "boAt", "JBL",
]


def extract_brand(title: str) -> Optional[str]:
    for brand in _KNOWN_BRANDS:
        if brand.lower() in title.lower():
            return brand
    return None


def extract_storage(title: str) -> Optional[str]:
    match = _STORAGE_PATTERN.search(title)
    if match:
        return f"{match.group(1)}{match.group(2).upper()}"
    return None


def extract_size(title: str) -> Optional[str]:
    match = _SIZE_PATTERN.search(title)
    if match:
        return f"{match.group(1)} inch"
    return None


def normalise_title(title: str) -> NormalisedProduct:
    brand = extract_brand(title)
    storage = extract_storage(title)
    size = extract_size(title)

    # Build canonical name by stripping marketing fluff
    canonical = title
    # Remove bracketed content like "(128 GB)"
    canonical = re.sub(r"\([^)]*\)", "", canonical)
    # Remove trailing dashes and extra spaces
    canonical = re.sub(r"\s*-\s*$", "", canonical).strip()
    canonical = re.sub(r"\s{2,}", " ", canonical)

    variant_parts = []
    if storage:
        variant_parts.append(storage)
    if size:
        variant_parts.append(size)

    return NormalisedProduct(
        canonical_name=canonical,
        brand=brand,
        storage=storage,
        size=size,
        variant_description=" ".join(variant_parts) if variant_parts else None,
        confidence=1.0,
    )

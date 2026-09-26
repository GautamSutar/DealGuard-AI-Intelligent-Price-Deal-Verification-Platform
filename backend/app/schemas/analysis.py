from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class PriceAnalysisSchema(BaseModel):
    listing_id: UUID
    marketplace: str
    title: str

    # Current prices
    current_price: Optional[float] = None
    current_effective_price: Optional[float] = None
    currency: str = "INR"

    # Historical statistics
    historical_average: Optional[float] = None
    historical_median: Optional[float] = None
    historical_minimum: Optional[float] = None
    historical_maximum: Optional[float] = None

    # Recent period averages
    avg_7d: Optional[float] = None
    avg_30d: Optional[float] = None
    avg_90d: Optional[float] = None

    # Percentage differences (negative = below = cheaper)
    pct_vs_average: Optional[float] = None
    pct_vs_median: Optional[float] = None
    pct_vs_minimum: Optional[float] = None
    pct_vs_maximum: Optional[float] = None

    # Position in historical range (0 = min, 1 = max)
    price_position: Optional[float] = None

    # Trend
    price_trend: Optional[str] = None  # RISING | FALLING | STABLE | VOLATILE

    # Coverage metadata
    observation_count: int = 0
    history_coverage_days: int = 0
    days_since_historical_low: Optional[int] = None

    # Rule-based classification (never LLM-generated)
    classification: Optional[str] = None
    classification_reasons: List[str] = []

    # Data transparency
    source: str = ""
    calculated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

"""
DealGuard Price Engine — deterministic calculations only.

The LLM is NEVER used here. Every number the AI quotes to a user must trace
back to a function in this module operating on real database records.
"""

from __future__ import annotations

import json
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import List, Optional


@dataclass
class PriceRecord:
    price: float
    observed_at: datetime
    source: str = "unknown"


@dataclass
class PriceEngineResult:
    # Inputs
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

    # Comparisons (negative = below historical = currently cheaper)
    pct_vs_average: Optional[float] = None
    pct_vs_median: Optional[float] = None
    pct_vs_minimum: Optional[float] = None
    pct_vs_maximum: Optional[float] = None

    # Normalised position in historical range (0 = min, 1 = max)
    price_position: Optional[float] = None

    # Trend
    price_trend: Optional[str] = None  # RISING | FALLING | STABLE | VOLATILE | INSUFFICIENT_DATA

    # Coverage metadata
    observation_count: int = 0
    history_coverage_days: int = 0
    days_since_historical_low: Optional[int] = None

    # Rule-based classification (not LLM)
    classification: Optional[str] = None
    classification_reasons: List[str] = field(default_factory=list)


def calculate_average(prices: List[float]) -> Optional[float]:
    if not prices:
        return None
    return round(statistics.mean(prices), 2)


def calculate_median(prices: List[float]) -> Optional[float]:
    if not prices:
        return None
    return round(statistics.median(prices), 2)


def calculate_minimum(prices: List[float]) -> Optional[float]:
    return round(min(prices), 2) if prices else None


def calculate_maximum(prices: List[float]) -> Optional[float]:
    return round(max(prices), 2) if prices else None


def calculate_percentile(prices: List[float], percentile: float) -> Optional[float]:
    if not prices:
        return None
    sorted_p = sorted(prices)
    k = (len(sorted_p) - 1) * percentile / 100
    f = int(k)
    c = f + 1
    if c >= len(sorted_p):
        return round(sorted_p[f], 2)
    return round(sorted_p[f] + (sorted_p[c] - sorted_p[f]) * (k - f), 2)


def calculate_percentage_difference(current: float, reference: float) -> Optional[float]:
    """Negative means current is BELOW reference (cheaper). Positive = more expensive."""
    if reference == 0:
        return None
    return round(((current - reference) / reference) * 100, 2)


def calculate_price_position(current: float, min_price: float, max_price: float) -> Optional[float]:
    """
    Returns a value in [0, 1]:
      0 = current equals historical minimum
      1 = current equals historical maximum

    Formula: (current - min) / (max - min)
    """
    if max_price == min_price:
        return 0.5
    position = (current - min_price) / (max_price - min_price)
    return round(max(0.0, min(1.0, position)), 3)


def calculate_data_coverage(records: List[PriceRecord]) -> int:
    """Returns number of calendar days spanned by the records."""
    if not records:
        return 0
    dates = [r.observed_at for r in records]
    return (max(dates) - min(dates)).days


def calculate_days_since_low(records: List[PriceRecord], min_price: float) -> Optional[int]:
    low_records = [r for r in records if abs(r.price - min_price) < 0.01]
    if not low_records:
        return None
    most_recent_low = max(r.observed_at for r in low_records)
    now = datetime.now(timezone.utc)
    if most_recent_low.tzinfo is None:
        most_recent_low = most_recent_low.replace(tzinfo=timezone.utc)
    return (now - most_recent_low).days


def _filter_by_days(records: List[PriceRecord], days: int) -> List[float]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    result = []
    for r in records:
        ts = r.observed_at
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        if ts >= cutoff:
            result.append(r.price)
    return result


def calculate_price_trend(records: List[PriceRecord]) -> str:
    """
    Compare short-term average (7d) against medium-term (90d).

    RISING   : 7d avg > 90d avg by more than 2%
    FALLING  : 7d avg < 90d avg by more than 2%
    STABLE   : difference within 2%
    VOLATILE : standard deviation > 10% of mean
    INSUFFICIENT_DATA: fewer than 3 records
    """
    if len(records) < 3:
        return "INSUFFICIENT_DATA"

    prices = [r.price for r in records]
    mean = statistics.mean(prices)
    if mean > 0:
        stdev = statistics.stdev(prices) if len(prices) > 1 else 0
        cv = stdev / mean  # coefficient of variation
        if cv > 0.10:
            return "VOLATILE"

    recent_7d = _filter_by_days(records, 7)
    recent_90d = _filter_by_days(records, 90)

    if not recent_7d or not recent_90d:
        return "INSUFFICIENT_DATA"

    avg_7 = statistics.mean(recent_7d)
    avg_90 = statistics.mean(recent_90d)

    if avg_90 == 0:
        return "INSUFFICIENT_DATA"

    pct_change = ((avg_7 - avg_90) / avg_90) * 100
    if pct_change > 2:
        return "RISING"
    elif pct_change < -2:
        return "FALLING"
    return "STABLE"


def classify_deal(result: PriceEngineResult) -> tuple[str, List[str]]:
    """
    Rule-based classification. Never uses the LLM.
    Returns (classification_label, list_of_human_readable_reasons).
    """
    if result.observation_count < 5 or result.history_coverage_days < 7:
        return "NEW_DATA_INSUFFICIENT", [
            f"Only {result.observation_count} observations over {result.history_coverage_days} days — "
            "insufficient history for reliable comparison."
        ]

    if result.current_effective_price is None or result.historical_average is None:
        return "NEW_DATA_INSUFFICIENT", ["Current price or historical average unavailable."]

    reasons: List[str] = []
    current = result.current_effective_price

    if result.pct_vs_average is not None:
        reasons.append(
            f"Current price is {abs(result.pct_vs_average):.1f}% "
            f"{'below' if result.pct_vs_average < 0 else 'above'} the historical average."
        )

    if result.pct_vs_minimum is not None:
        reasons.append(
            f"Current price is {abs(result.pct_vs_minimum):.1f}% "
            f"{'above' if result.pct_vs_minimum > 0 else 'below'} the historical minimum."
        )

    if result.history_coverage_days:
        reasons.append(f"History coverage: {result.history_coverage_days} days, {result.observation_count} observations.")

    # Determine label
    pct = result.pct_vs_average
    pos = result.price_position

    if result.price_trend in ("RISING",):
        label = "PRICE_INCREASING"
    elif result.price_trend in ("FALLING",):
        label = "PRICE_DECREASING"
    elif result.price_trend == "VOLATILE":
        label = "PRICE_VOLATILE"
    elif pos is not None and pos <= 0.10:
        label = "NEAR_HISTORICAL_LOW"
    elif pct is not None and pct < -5:
        label = "BELOW_HISTORICAL_AVERAGE"
    elif pct is not None and -5 <= pct <= 5:
        label = "AROUND_HISTORICAL_AVERAGE"
    else:
        label = "ABOVE_HISTORICAL_AVERAGE"

    return label, reasons


def run_price_engine(
    current_price: float,
    records: List[PriceRecord],
    current_effective_price: Optional[float] = None,
    currency: str = "INR",
) -> PriceEngineResult:
    """
    Main entry point. Accepts raw price records and returns a fully populated
    PriceEngineResult with all statistics. No I/O, no LLM calls.
    """
    result = PriceEngineResult(
        current_price=round(current_price, 2),
        current_effective_price=round(current_effective_price or current_price, 2),
        currency=currency,
        observation_count=len(records),
        history_coverage_days=calculate_data_coverage(records),
    )

    if not records:
        result.classification = "NEW_DATA_INSUFFICIENT"
        result.classification_reasons = ["No historical price data available yet."]
        return result

    prices = [r.price for r in records]
    effective_price = result.current_effective_price

    result.historical_average = calculate_average(prices)
    result.historical_median = calculate_median(prices)
    result.historical_minimum = calculate_minimum(prices)
    result.historical_maximum = calculate_maximum(prices)

    result.avg_7d = calculate_average(_filter_by_days(records, 7)) if _filter_by_days(records, 7) else None
    result.avg_30d = calculate_average(_filter_by_days(records, 30)) if _filter_by_days(records, 30) else None
    result.avg_90d = calculate_average(_filter_by_days(records, 90)) if _filter_by_days(records, 90) else None

    if result.historical_average:
        result.pct_vs_average = calculate_percentage_difference(effective_price, result.historical_average)
    if result.historical_median:
        result.pct_vs_median = calculate_percentage_difference(effective_price, result.historical_median)
    if result.historical_minimum:
        result.pct_vs_minimum = calculate_percentage_difference(effective_price, result.historical_minimum)
        result.days_since_historical_low = calculate_days_since_low(records, result.historical_minimum)
    if result.historical_maximum:
        result.pct_vs_maximum = calculate_percentage_difference(effective_price, result.historical_maximum)

    if result.historical_minimum is not None and result.historical_maximum is not None:
        result.price_position = calculate_price_position(
            effective_price, result.historical_minimum, result.historical_maximum
        )

    result.price_trend = calculate_price_trend(records)
    result.classification, result.classification_reasons = classify_deal(result)

    return result

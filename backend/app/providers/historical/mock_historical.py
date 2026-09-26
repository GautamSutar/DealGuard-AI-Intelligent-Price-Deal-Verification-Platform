"""
Mock historical provider — generates synthetic price history for development.

Generates realistic price fluctuations over the past N days so the price
engine has data to work with before a real provider is integrated.
This data is SYNTHETIC — always labelled source='mock_historical'.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from typing import List

from app.providers.historical.base import HistoricalProvider
from app.providers.marketplace.base import ProviderHistoryRecord

# Base prices for known ASINs
MOCK_BASE_PRICES = {
    "B0CHX1W1XY": 72500.0,   # iPhone 16 128GB
    "B0CSMP4B1J": 48000.0,   # Samsung TV 55
    "B09XS7JWHH": 25000.0,   # Sony WH-1000XM5
}
DEFAULT_BASE = 50000.0


class MockHistoricalProvider(HistoricalProvider):
    @property
    def provider_name(self) -> str:
        return "mock_historical"

    async def get_history(
        self,
        external_id: str,
        marketplace: str,
        days: int = 365,
    ) -> List[ProviderHistoryRecord]:
        base_price = MOCK_BASE_PRICES.get(external_id, DEFAULT_BASE)
        records = []
        now = datetime.now(timezone.utc)

        for day_offset in range(days, 0, -1):
            # Realistic price fluctuation: ±15% around base, occasional spikes
            noise = random.gauss(0, 0.04)
            seasonal = 0.05 * (1 if day_offset % 90 < 10 else 0)  # Sale events
            factor = 1 + noise - seasonal
            price = round(base_price * factor, 2)
            mrp = round(base_price * 1.15, 2)

            records.append(
                ProviderHistoryRecord(
                    external_id=external_id,
                    marketplace=marketplace,
                    observed_at=now - timedelta(days=day_offset),
                    selling_price=price,
                    mrp=mrp,
                    effective_price=price,
                    currency="INR",
                    source="mock_historical",
                    confidence=0.9,
                )
            )

        return records

"""Base abstraction for historical price data providers (e.g. Keepa)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from app.providers.marketplace.base import ProviderHistoryRecord


class HistoricalProvider(ABC):
    """
    Interface for providers that supply historical price data.

    MODE A: External API (e.g. Keepa) — bootstraps history immediately.
    MODE B: Own collector — builds history gradually via Celery tasks.

    Both modes return the same ProviderHistoryRecord type so the rest of
    the system is agnostic about the source.
    """

    @abstractmethod
    async def get_history(
        self,
        external_id: str,
        marketplace: str,
        days: int = 365,
    ) -> List[ProviderHistoryRecord]:
        """Return historical price records for the given product."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Short identifier: 'keepa' | 'our_collector' etc."""

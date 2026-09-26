"""
Analysis service — bridges database records to the price engine.

The price engine (price_engine.py) is purely functional.
This service retrieves records from the DB, feeds them to the engine,
and persists the result.
"""

from __future__ import annotations

import json
from typing import Optional
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.listing import ProductListing
from app.models.price_analysis import PriceAnalysis
from app.models.price_history import PriceHistory
from app.schemas.analysis import PriceAnalysisSchema
from app.utils.price_engine import PriceRecord, run_price_engine

logger = structlog.get_logger(__name__)


async def get_or_calculate_analysis(
    db: AsyncSession,
    listing_id: UUID,
    force_recalculate: bool = False,
) -> Optional[PriceAnalysisSchema]:
    """
    Returns a PriceAnalysisSchema.
    If a recent analysis exists in DB and force_recalculate is False, returns cached.
    Otherwise recalculates from raw price_history records.
    """
    listing = await db.get(ProductListing, listing_id)
    if not listing:
        logger.warning("Listing not found", listing_id=str(listing_id))
        return None

    if not force_recalculate:
        result = await db.execute(
            select(PriceAnalysis)
            .where(PriceAnalysis.product_listing_id == listing_id)
            .order_by(PriceAnalysis.calculated_at.desc())
            .limit(1)
        )
        cached = result.scalar_one_or_none()
        if cached:
            return _analysis_to_schema(cached, listing)

    return await _recalculate_and_store(db, listing)


async def _recalculate_and_store(db: AsyncSession, listing: ProductListing) -> Optional[PriceAnalysisSchema]:
    history_result = await db.execute(
        select(PriceHistory)
        .where(PriceHistory.product_listing_id == listing.id)
        .order_by(PriceHistory.observed_at.asc())
    )
    rows = history_result.scalars().all()

    if not rows:
        logger.info("No price history found", listing_id=str(listing.id))
        return None

    records = [PriceRecord(price=float(r.selling_price), observed_at=r.observed_at, source=r.source_type) for r in rows]
    latest = rows[-1]
    current_price = float(latest.selling_price)
    current_effective = float(latest.effective_price) if latest.effective_price else current_price

    engine_result = run_price_engine(
        current_price=current_price,
        records=records,
        current_effective_price=current_effective,
        currency=latest.currency,
    )

    # Persist analysis
    analysis = PriceAnalysis(
        product_listing_id=listing.id,
        current_price=engine_result.current_price,
        current_effective_price=engine_result.current_effective_price,
        historical_average=engine_result.historical_average,
        historical_median=engine_result.historical_median,
        historical_minimum=engine_result.historical_minimum,
        historical_maximum=engine_result.historical_maximum,
        avg_7d=engine_result.avg_7d,
        avg_30d=engine_result.avg_30d,
        avg_90d=engine_result.avg_90d,
        pct_vs_average=engine_result.pct_vs_average,
        pct_vs_median=engine_result.pct_vs_median,
        pct_vs_minimum=engine_result.pct_vs_minimum,
        pct_vs_maximum=engine_result.pct_vs_maximum,
        price_position=engine_result.price_position,
        price_trend=engine_result.price_trend,
        observation_count=engine_result.observation_count,
        history_coverage_days=engine_result.history_coverage_days,
        days_since_historical_low=engine_result.days_since_historical_low,
        classification=engine_result.classification,
        classification_reasons=json.dumps(engine_result.classification_reasons),
    )
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)

    return _analysis_to_schema(analysis, listing)


def _analysis_to_schema(analysis: PriceAnalysis, listing: ProductListing) -> PriceAnalysisSchema:
    reasons = []
    if analysis.classification_reasons:
        try:
            reasons = json.loads(analysis.classification_reasons)
        except Exception:
            reasons = [analysis.classification_reasons]

    return PriceAnalysisSchema(
        listing_id=analysis.product_listing_id,
        marketplace="amazon",  # TODO: join with marketplace table
        title=listing.title,
        current_price=float(analysis.current_price) if analysis.current_price else None,
        current_effective_price=float(analysis.current_effective_price) if analysis.current_effective_price else None,
        historical_average=float(analysis.historical_average) if analysis.historical_average else None,
        historical_median=float(analysis.historical_median) if analysis.historical_median else None,
        historical_minimum=float(analysis.historical_minimum) if analysis.historical_minimum else None,
        historical_maximum=float(analysis.historical_maximum) if analysis.historical_maximum else None,
        avg_7d=float(analysis.avg_7d) if analysis.avg_7d else None,
        avg_30d=float(analysis.avg_30d) if analysis.avg_30d else None,
        avg_90d=float(analysis.avg_90d) if analysis.avg_90d else None,
        pct_vs_average=float(analysis.pct_vs_average) if analysis.pct_vs_average else None,
        pct_vs_median=float(analysis.pct_vs_median) if analysis.pct_vs_median else None,
        pct_vs_minimum=float(analysis.pct_vs_minimum) if analysis.pct_vs_minimum else None,
        pct_vs_maximum=float(analysis.pct_vs_maximum) if analysis.pct_vs_maximum else None,
        price_position=float(analysis.price_position) if analysis.price_position else None,
        price_trend=analysis.price_trend,
        observation_count=analysis.observation_count or 0,
        history_coverage_days=analysis.history_coverage_days or 0,
        days_since_historical_low=analysis.days_since_historical_low,
        classification=analysis.classification,
        classification_reasons=reasons,
        calculated_at=analysis.calculated_at,
    )

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PriceAnalysis(Base):
    """
    Cached result of the deterministic price engine for a product listing.

    classification values (rule-based, not LLM-generated):
      NEAR_HISTORICAL_LOW | BELOW_HISTORICAL_AVERAGE | AROUND_HISTORICAL_AVERAGE |
      ABOVE_HISTORICAL_AVERAGE | NEW_DATA_INSUFFICIENT | PRICE_INCREASING |
      PRICE_DECREASING | PRICE_VOLATILE
    """

    __tablename__ = "price_analysis"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_listings.id"), nullable=False
    )

    # Current snapshot used for analysis
    current_price: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    current_effective_price: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)

    # Historical statistics (all from observed selling prices, never MRP)
    historical_average: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    historical_median: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    historical_minimum: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    historical_maximum: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)

    # Recent period averages
    avg_7d: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    avg_30d: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    avg_90d: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)

    # Percentage comparisons (negative = below average = cheaper)
    pct_vs_average: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    pct_vs_median: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    pct_vs_minimum: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    pct_vs_maximum: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)

    # Position: 0 = historical min, 1 = historical max
    price_position: Mapped[float | None] = mapped_column(Numeric(4, 3), nullable=True)

    # Trend
    price_trend: Mapped[str | None] = mapped_column(String(20), nullable=True)  # RISING | FALLING | STABLE | VOLATILE

    # Coverage metadata
    observation_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    history_coverage_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    days_since_historical_low: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Rule-based classification
    classification: Mapped[str | None] = mapped_column(String(50), nullable=True)
    classification_reasons: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array of reason strings

    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    listing: Mapped["ProductListing"] = relationship("ProductListing", back_populates="analyses")

    def __repr__(self) -> str:
        return f"<PriceAnalysis listing={self.product_listing_id} classification={self.classification}>"

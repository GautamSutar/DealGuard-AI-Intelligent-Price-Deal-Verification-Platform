import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PriceHistory(Base):
    """
    Each row is one observed price snapshot for a product listing.

    source_type distinguishes:
      - 'external_api'   : bootstrapped from a third-party historical provider (e.g. Keepa)
      - 'our_collector'  : collected by DealGuard's own Celery scheduler
      - 'marketplace_api': retrieved directly from a marketplace API
    """

    __tablename__ = "price_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_listings.id"), nullable=False
    )
    seller_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("sellers.id"), nullable=True)

    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Prices — always stored as NUMERIC, formatted only at presentation time
    mrp: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    selling_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    effective_price: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)

    currency: Mapped[str] = mapped_column(String(3), default="INR")
    availability: Mapped[bool] = mapped_column(Boolean, default=True)

    # Data provenance
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)  # external_api / our_collector / marketplace_api
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)  # e.g. "keepa", "amazon_api"
    confidence_score: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)  # 0.00 – 1.00

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    listing: Mapped["ProductListing"] = relationship("ProductListing", back_populates="price_histories")
    seller: Mapped["Seller | None"] = relationship("Seller", back_populates="price_histories")

    __table_args__ = (
        Index("ix_price_history_listing_observed", "product_listing_id", "observed_at"),
        Index("ix_price_history_listing_observed_desc", "product_listing_id", "observed_at"),
    )

    def __repr__(self) -> str:
        return f"<PriceHistory listing={self.product_listing_id} price={self.selling_price} at={self.observed_at}>"

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ProductListing(Base):
    """A product as listed on a specific marketplace (ASIN on Amazon, etc.)."""

    __tablename__ = "product_listings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    marketplace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("marketplaces.id"), nullable=False)

    # Marketplace-specific identifiers
    external_product_id: Mapped[str] = mapped_column(String(255), nullable=False)  # ASIN, Flipkart ID
    url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    title: Mapped[str] = mapped_column(String(1000), nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Variant information
    variant_description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Availability
    availability: Mapped[bool] = mapped_column(Boolean, default=True)
    currency: Mapped[str] = mapped_column(String(3), default="INR")

    # Tracking timestamps
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    product: Mapped["Product"] = relationship("Product", back_populates="listings")
    marketplace: Mapped["Marketplace"] = relationship("Marketplace", back_populates="listings")
    price_histories: Mapped[list["PriceHistory"]] = relationship("PriceHistory", back_populates="listing")
    offers: Mapped[list["Offer"]] = relationship("Offer", back_populates="listing")
    analyses: Mapped[list["PriceAnalysis"]] = relationship("PriceAnalysis", back_populates="listing")

    def __repr__(self) -> str:
        return f"<ProductListing {self.external_product_id} on {self.marketplace_id}>"

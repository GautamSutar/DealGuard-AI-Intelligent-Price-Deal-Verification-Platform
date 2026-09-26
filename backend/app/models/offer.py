import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Offer(Base):
    """
    Represents a single offer/promotion on a product listing.

    offer_type can be:
      - 'coupon'         : clip-and-apply coupon
      - 'bank'           : bank/card-specific instant discount
      - 'exchange'       : exchange offer
      - 'membership'     : Prime / Flipkart Plus etc.
      - 'app_only'       : discount only via mobile app
      - 'seller'         : seller-specific discount
      - 'bundle'         : bundle deal
      - 'seasonal'       : sale event (Diwali, etc.)

    eligibility stores human-readable conditions (e.g., "HDFC credit card").
    The system does NOT auto-apply conditional offers to the base price.
    """

    __tablename__ = "offers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_listings.id"), nullable=False
    )

    offer_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    discount_value: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    discount_percentage: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    coupon_code: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Eligibility constraints
    eligibility: Mapped[str | None] = mapped_column(String(500), nullable=True)
    conditions: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_conditional: Mapped[bool] = mapped_column(default=False)

    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    source: Mapped[str | None] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    listing: Mapped["ProductListing"] = relationship("ProductListing", back_populates="offers")

    def __repr__(self) -> str:
        return f"<Offer {self.offer_type} value={self.discount_value}>"

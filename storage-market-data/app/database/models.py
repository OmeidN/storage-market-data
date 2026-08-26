from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class FacilityRow(Base):
    __tablename__ = "facilities"
    __table_args__ = (
        UniqueConstraint("provider", "slug", name="uq_facilities_provider_slug"),
        UniqueConstraint("url", name="uq_facilities_url"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, nullable=False)
    url: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    address: Mapped[str | None] = mapped_column(String, nullable=True)
    asset_type: Mapped[str] = mapped_column(
        String, nullable=False, server_default="self_storage"
    )
    attributes: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    units: Mapped[list[UnitRow]] = relationship(back_populates="facility")


class UnitRow(Base):
    """Rentable space product. Table name stays `units` (Listing in Pydantic)."""

    __tablename__ = "units"
    __table_args__ = (
        UniqueConstraint("facility_id", "identity_key", name="uq_units_facility_identity"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    facility_id: Mapped[int] = mapped_column(
        ForeignKey("facilities.id"), nullable=False, index=True
    )
    identity_key: Mapped[str] = mapped_column(String, nullable=False)
    provider_unit_id: Mapped[str | None] = mapped_column(String, nullable=True)
    square_footage: Mapped[int] = mapped_column(Integer, nullable=False)
    width_ft: Mapped[int | None] = mapped_column(Integer, nullable=True)
    length_ft: Mapped[int | None] = mapped_column(Integer, nullable=True)
    features: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    attributes: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    price_data_available: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )

    facility: Mapped[FacilityRow] = relationship(back_populates="units")
    observations: Mapped[list[ObservationRow]] = relationship(back_populates="unit")


class ObservationRow(Base):
    __tablename__ = "observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    unit_id: Mapped[int] = mapped_column(
        ForeignKey("units.id"), nullable=False, index=True
    )
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    price_unit: Mapped[str | None] = mapped_column(String, nullable=True)
    price_data_available: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    standard_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    promo_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    availability_status: Mapped[str] = mapped_column(String, nullable=False)
    availability_text: Mapped[str | None] = mapped_column(String, nullable=True)
    free_first_month: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    parse_strategy: Mapped[str | None] = mapped_column(String, nullable=True)

    unit: Mapped[UnitRow] = relationship(back_populates="observations")

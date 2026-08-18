"""
Normalized Pydantic models for a parsed facility page.

The StorQuest parser still returns plain dicts. This module is the
validation layer: malformed sizes, missing prices, and similar problems
raise ValidationError instead of becoming silently wrong observations.

AvailabilityStatus is explicit. A missing unit list is not the same as
sold out (planning.md §88 / §23).
"""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, computed_field, model_validator


class AvailabilityStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    LIMITED = "LIMITED"
    SOLD_OUT = "SOLD_OUT"
    UNKNOWN = "UNKNOWN"


class ParseStatus(StrEnum):
    OK = "OK"
    NO_UNITS = "NO_UNITS"
    FAILED = "FAILED"


class Facility(BaseModel):
    provider: str
    slug: str
    url: str
    name: str | None = None
    address: str | None = None


class Unit(BaseModel):
    provider_unit_id: str | None = None
    width_ft: int = Field(..., gt=0)
    length_ft: int = Field(..., gt=0)
    features: list[str] = Field(default_factory=list)
    standard_price: int | None = Field(default=None, ge=0)
    promo_price: int | None = Field(default=None, ge=0)
    availability_status: AvailabilityStatus
    availability_text: str | None = None
    free_first_month: bool = False

    @model_validator(mode="after")
    def require_a_price(self) -> Unit:
        if self.standard_price is None and self.promo_price is None:
            raise ValueError("at least one of standard_price or promo_price is required")
        return self

    @computed_field
    @property
    def identity_key(self) -> str:
        if self.provider_unit_id:
            return self.provider_unit_id
        feats = "|".join(sorted(self.features))
        return f"{self.width_ft}x{self.length_ft}|{feats}"


class Observation(BaseModel):
    """A single append-only price/availability snapshot for one unit."""

    identity_key: str
    scraped_at: datetime
    standard_price: int | None = Field(default=None, ge=0)
    promo_price: int | None = Field(default=None, ge=0)
    availability_status: AvailabilityStatus
    availability_text: str | None = None
    free_first_month: bool = False
    parse_strategy: str | None = None


class FacilityPage(BaseModel):
    parse_status: ParseStatus
    parse_strategy: str | None = None
    facility: Facility
    units: list[Unit] = Field(default_factory=list)
    scraped_at: datetime | None = None

    @model_validator(mode="after")
    def status_matches_units(self) -> FacilityPage:
        if self.parse_status == ParseStatus.OK and not self.units:
            raise ValueError("OK parse must include units")
        if self.parse_status in (ParseStatus.NO_UNITS, ParseStatus.FAILED) and self.units:
            raise ValueError(f"{self.parse_status} parse must not include units")
        return self

    def observations(self) -> list[Observation]:
        if (
            self.parse_status != ParseStatus.OK
            or not self.units
            or self.scraped_at is None
        ):
            return []
        return [
            Observation(
                identity_key=unit.identity_key,
                scraped_at=self.scraped_at,
                standard_price=unit.standard_price,
                promo_price=unit.promo_price,
                availability_status=unit.availability_status,
                availability_text=unit.availability_text,
                free_first_month=unit.free_first_month,
                parse_strategy=self.parse_strategy,
            )
            for unit in self.units
        ]


def availability_status_from_parse(unit: dict[str, Any]) -> AvailabilityStatus:
    count = unit.get("rentable_units_count")
    if isinstance(count, bool):
        count = None
    if isinstance(count, (int, float)):
        if count <= 0:
            return AvailabilityStatus.SOLD_OUT
        if count <= 5:
            return AvailabilityStatus.LIMITED
        return AvailabilityStatus.AVAILABLE

    text = (unit.get("availability_text") or "").strip().lower()
    if "sold out" in text:
        return AvailabilityStatus.SOLD_OUT
    if "limited" in text or "left" in text:
        return AvailabilityStatus.LIMITED
    return AvailabilityStatus.UNKNOWN


def unit_from_parse(raw: dict[str, Any]) -> Unit:
    return Unit(
        provider_unit_id=raw.get("provider_unit_id"),
        width_ft=raw.get("width_ft"),
        length_ft=raw.get("length_ft"),
        features=list(raw.get("features") or []),
        standard_price=raw.get("standard_price"),
        promo_price=raw.get("promo_price"),
        availability_status=availability_status_from_parse(raw),
        availability_text=raw.get("availability_text"),
        free_first_month=bool(raw.get("free_first_month", False)),
    )


def facility_page_from_parse(
    parsed: dict[str, Any],
    *,
    provider: str,
    slug: str,
    url: str,
    scraped_at: datetime | None = None,
) -> FacilityPage:
    """
    Validate parser output into a FacilityPage.

    Raises ValidationError if units are present but malformed.
    A missing or empty unit list becomes FAILED / NO_UNITS rather than
    a list of sold-out units.
    """
    facility = Facility(
        provider=provider,
        slug=slug,
        url=url,
        name=parsed.get("facility_name"),
        address=parsed.get("address"),
    )
    strategy = parsed.get("parse_strategy")
    raw_units = parsed.get("units")

    if raw_units is None:
        return FacilityPage(
            parse_status=ParseStatus.FAILED,
            parse_strategy=strategy,
            facility=facility,
            units=[],
            scraped_at=scraped_at,
        )

    if len(raw_units) == 0:
        status = (
            ParseStatus.NO_UNITS
            if strategy == "next_data_json"
            else ParseStatus.FAILED
        )
        return FacilityPage(
            parse_status=status,
            parse_strategy=strategy,
            facility=facility,
            units=[],
            scraped_at=scraped_at,
        )

    return FacilityPage(
        parse_status=ParseStatus.OK,
        parse_strategy=strategy,
        facility=facility,
        units=[unit_from_parse(raw) for raw in raw_units],
        scraped_at=scraped_at,
    )

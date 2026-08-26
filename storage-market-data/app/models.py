"""
Normalized Pydantic models for a parsed facility page.

Provider parsers still return plain dicts. This module is the
validation layer: malformed sizes, missing prices (when the provider
publishes them), and similar problems raise ValidationError instead of
becoming silently wrong observations.

Listing is vertical-agnostic (square footage, price, price_unit).
Storage-specific fields live in attributes. A missing listing list is
not the same as sold out (planning.md §88 / §23).
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


class AssetType(StrEnum):
    SELF_STORAGE = "self_storage"
    WAREHOUSE_INDUSTRIAL = "warehouse_industrial"


class PriceUnit(StrEnum):
    PER_UNIT_PER_MONTH = "per_unit_per_month"
    PER_SQFT_PER_YEAR = "per_sqft_per_year"
    PER_SQFT_PER_MONTH = "per_sqft_per_month"


class Facility(BaseModel):
    provider: str
    slug: str
    url: str
    name: str | None = None
    address: str | None = None
    asset_type: AssetType = AssetType.SELF_STORAGE
    attributes: dict[str, Any] = Field(default_factory=dict)


class Listing(BaseModel):
    """A rentable space product. Postgres table remains `units`."""

    provider_unit_id: str | None = None
    square_footage: int = Field(..., gt=0)
    price: int | None = Field(default=None, ge=0)
    price_unit: PriceUnit | None = None
    price_data_available: bool = True
    availability_status: AvailabilityStatus
    availability_text: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _coerce_storage_shape(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        d = dict(data)
        attrs = dict(d.get("attributes") or {})

        width = d.pop("width_ft", None) if "width_ft" in d else None
        length = d.pop("length_ft", None) if "length_ft" in d else None
        features = d.pop("features", None) if "features" in d else None
        standard = d.pop("standard_price") if "standard_price" in d else None
        promo = d.pop("promo_price") if "promo_price" in d else None
        free = d.pop("free_first_month") if "free_first_month" in d else None

        if width is not None:
            attrs.setdefault("width_ft", width)
        if length is not None:
            attrs.setdefault("length_ft", length)
        if features is not None:
            attrs.setdefault("features", list(features))
        if "standard_price" in data:
            attrs.setdefault("standard_price", standard)
        if "promo_price" in data:
            attrs.setdefault("promo_price", promo)
        if free is not None:
            attrs.setdefault("free_first_month", bool(free))

        if d.get("square_footage") is None and width and length:
            try:
                d["square_footage"] = int(width) * int(length)
            except (TypeError, ValueError):
                pass
        if d.get("price") is None:
            if standard is not None:
                d["price"] = standard
            elif promo is not None:
                d["price"] = promo
        price_available = d.get("price_data_available", True)
        storage_shaped = width is not None or length is not None or "standard_price" in data
        if d.get("price_unit") is None and price_available and storage_shaped:
            d["price_unit"] = PriceUnit.PER_UNIT_PER_MONTH

        d["attributes"] = attrs
        return d

    @model_validator(mode="after")
    def require_a_price_when_published(self) -> Listing:
        if self.price_data_available and self.price is None:
            raise ValueError("price is required when price_data_available is true")
        return self

    @computed_field
    @property
    def identity_key(self) -> str:
        if self.provider_unit_id:
            return self.provider_unit_id
        feats = self.attributes.get("features") or []
        feat_key = "|".join(sorted(str(f) for f in feats))
        return f"{self.square_footage}|{feat_key}"

    @property
    def width_ft(self) -> int | None:
        value = self.attributes.get("width_ft")
        return int(value) if value is not None else None

    @property
    def length_ft(self) -> int | None:
        value = self.attributes.get("length_ft")
        return int(value) if value is not None else None

    @property
    def features(self) -> list[str]:
        return list(self.attributes.get("features") or [])

    @property
    def standard_price(self) -> int | None:
        if "standard_price" in self.attributes:
            value = self.attributes["standard_price"]
            return int(value) if value is not None else None
        return self.price

    @property
    def promo_price(self) -> int | None:
        value = self.attributes.get("promo_price")
        return int(value) if value is not None else None

    @property
    def free_first_month(self) -> bool:
        return bool(self.attributes.get("free_first_month", False))


# Compatibility alias — Postgres table and older tests still say "unit".
Unit = Listing


class Observation(BaseModel):
    """A single append-only price/availability snapshot for one listing."""

    identity_key: str
    scraped_at: datetime
    price: int | None = Field(default=None, ge=0)
    price_unit: PriceUnit | None = None
    price_data_available: bool = True
    standard_price: int | None = Field(default=None, ge=0)
    promo_price: int | None = Field(default=None, ge=0)
    availability_status: AvailabilityStatus
    availability_text: str | None = None
    free_first_month: bool = False
    parse_strategy: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class FacilityPage(BaseModel):
    parse_status: ParseStatus
    parse_strategy: str | None = None
    facility: Facility
    listings: list[Listing] = Field(default_factory=list)
    scraped_at: datetime | None = None

    @model_validator(mode="before")
    @classmethod
    def _units_alias(cls, data: Any) -> Any:
        if isinstance(data, dict) and "units" in data and "listings" not in data:
            data = {**data, "listings": data["units"]}
        return data

    @property
    def units(self) -> list[Listing]:
        return self.listings

    @model_validator(mode="after")
    def status_matches_units(self) -> FacilityPage:
        if self.parse_status == ParseStatus.OK and not self.listings:
            raise ValueError("OK parse must include listings")
        if self.parse_status in (ParseStatus.NO_UNITS, ParseStatus.FAILED) and self.listings:
            raise ValueError(f"{self.parse_status} parse must not include listings")
        return self

    def observations(self) -> list[Observation]:
        if (
            self.parse_status != ParseStatus.OK
            or not self.listings
            or self.scraped_at is None
        ):
            return []
        return [
            Observation(
                identity_key=listing.identity_key,
                scraped_at=self.scraped_at,
                price=listing.price,
                price_unit=listing.price_unit,
                price_data_available=listing.price_data_available,
                standard_price=listing.standard_price,
                promo_price=listing.promo_price,
                availability_status=listing.availability_status,
                availability_text=listing.availability_text,
                free_first_month=listing.free_first_month,
                parse_strategy=self.parse_strategy,
                attributes=dict(listing.attributes),
            )
            for listing in self.listings
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


def listing_from_parse(raw: dict[str, Any]) -> Listing:
    payload = dict(raw)
    if "availability_status" not in payload:
        payload["availability_status"] = availability_status_from_parse(raw)
    return Listing.model_validate(payload)


def unit_from_parse(raw: dict[str, Any]) -> Listing:
    return listing_from_parse(raw)


def facility_page_from_parse(
    parsed: dict[str, Any],
    *,
    provider: str,
    slug: str,
    url: str,
    scraped_at: datetime | None = None,
    asset_type: AssetType | None = None,
) -> FacilityPage:
    """
    Validate parser output into a FacilityPage.

    Raises ValidationError if listings are present but malformed.
    A missing or empty listing list becomes FAILED / NO_UNITS rather than
    a list of sold-out listings.
    """
    resolved_type = asset_type
    if resolved_type is None:
        raw_type = parsed.get("asset_type")
        resolved_type = (
            AssetType(raw_type) if raw_type else AssetType.SELF_STORAGE
        )
    facility = Facility(
        provider=provider,
        slug=slug,
        url=url,
        name=parsed.get("facility_name"),
        address=parsed.get("address"),
        asset_type=resolved_type,
        attributes=dict(parsed.get("facility_attributes") or {}),
    )
    strategy = parsed.get("parse_strategy")
    raw_units = parsed.get("units")
    if raw_units is None:
        raw_units = parsed.get("listings")

    if raw_units is None:
        return FacilityPage(
            parse_status=ParseStatus.FAILED,
            parse_strategy=strategy,
            facility=facility,
            listings=[],
            scraped_at=scraped_at,
        )

    if len(raw_units) == 0:
        status = ParseStatus.NO_UNITS if strategy else ParseStatus.FAILED
        return FacilityPage(
            parse_status=status,
            parse_strategy=strategy,
            facility=facility,
            listings=[],
            scraped_at=scraped_at,
        )

    return FacilityPage(
        parse_status=ParseStatus.OK,
        parse_strategy=strategy,
        facility=facility,
        listings=[listing_from_parse(raw) for raw in raw_units],
        scraped_at=scraped_at,
    )

"""Persist a validated FacilityPage. Observations are append-only."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.engine import session_factory
from app.database.models import FacilityRow, ObservationRow, UnitRow
from app.models import FacilityPage, ParseStatus


def save_observation(
    page: FacilityPage,
    *,
    scraped_at: datetime,
    url: str | None = None,
    session: Session | None = None,
) -> None:
    """
    Upsert facility and units; always INSERT a new observation row.

    Writes nothing when parse_status is not OK or the listing list is empty,
    so a failed scrape cannot be recorded as sold out.
    """
    if page.parse_status != ParseStatus.OK or not page.listings:
        return

    own_session = session is None
    if own_session:
        session = session_factory()()
    assert session is not None

    try:
        _save(session, page, scraped_at=scraped_at, url=url)
        if own_session:
            session.commit()
    except Exception:
        if own_session:
            session.rollback()
        raise
    finally:
        if own_session:
            session.close()


def _save(
    session: Session,
    page: FacilityPage,
    *,
    scraped_at: datetime,
    url: str | None,
) -> None:
    facility_url = url or page.facility.url
    facility = session.scalar(
        select(FacilityRow).where(
            FacilityRow.provider == page.facility.provider,
            FacilityRow.slug == page.facility.slug,
        )
    )
    if facility is None:
        facility = FacilityRow(
            provider=page.facility.provider,
            slug=page.facility.slug,
            url=facility_url,
            name=page.facility.name,
            address=page.facility.address,
            asset_type=page.facility.asset_type.value,
            attributes=dict(page.facility.attributes),
        )
        session.add(facility)
        session.flush()
    else:
        facility.url = facility_url
        facility.name = page.facility.name
        facility.address = page.facility.address
        facility.asset_type = page.facility.asset_type.value
        facility.attributes = dict(page.facility.attributes)

    for listing in page.listings:
        attrs = dict(listing.attributes)
        row = session.scalar(
            select(UnitRow).where(
                UnitRow.facility_id == facility.id,
                UnitRow.identity_key == listing.identity_key,
            )
        )
        if row is None:
            row = UnitRow(
                facility_id=facility.id,
                identity_key=listing.identity_key,
                provider_unit_id=listing.provider_unit_id,
                square_footage=listing.square_footage,
                width_ft=listing.width_ft,
                length_ft=listing.length_ft,
                features=list(listing.features),
                attributes=attrs,
                price_data_available=listing.price_data_available,
            )
            session.add(row)
            session.flush()
        else:
            row.provider_unit_id = listing.provider_unit_id
            row.square_footage = listing.square_footage
            row.width_ft = listing.width_ft
            row.length_ft = listing.length_ft
            row.features = list(listing.features)
            row.attributes = attrs
            row.price_data_available = listing.price_data_available

        session.add(
            ObservationRow(
                unit_id=row.id,
                scraped_at=scraped_at,
                price=listing.price,
                price_unit=listing.price_unit.value if listing.price_unit else None,
                price_data_available=listing.price_data_available,
                standard_price=listing.standard_price,
                promo_price=listing.promo_price,
                availability_status=listing.availability_status.value,
                availability_text=listing.availability_text,
                free_first_month=listing.free_first_month,
                parse_strategy=page.parse_strategy,
            )
        )

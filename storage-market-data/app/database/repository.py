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

    Writes nothing when parse_status is not OK or the unit list is empty,
    so a failed scrape cannot be recorded as sold out.
    """
    if page.parse_status != ParseStatus.OK or not page.units:
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
        )
        session.add(facility)
        session.flush()
    else:
        facility.url = facility_url
        facility.name = page.facility.name
        facility.address = page.facility.address

    for unit in page.units:
        row = session.scalar(
            select(UnitRow).where(
                UnitRow.facility_id == facility.id,
                UnitRow.identity_key == unit.identity_key,
            )
        )
        if row is None:
            row = UnitRow(
                facility_id=facility.id,
                identity_key=unit.identity_key,
                provider_unit_id=unit.provider_unit_id,
                width_ft=unit.width_ft,
                length_ft=unit.length_ft,
                features=list(unit.features),
            )
            session.add(row)
            session.flush()
        else:
            row.provider_unit_id = unit.provider_unit_id
            row.width_ft = unit.width_ft
            row.length_ft = unit.length_ft
            row.features = list(unit.features)

        session.add(
            ObservationRow(
                unit_id=row.id,
                scraped_at=scraped_at,
                standard_price=unit.standard_price,
                promo_price=unit.promo_price,
                availability_status=unit.availability_status.value,
                availability_text=unit.availability_text,
                free_first_month=unit.free_first_month,
                parse_strategy=page.parse_strategy,
            )
        )

"""Postgres repository tests. Skipped when no test database URL is configured."""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, inspect, select, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker

from app.database.models import Base, FacilityRow, ObservationRow, UnitRow
from app.database.repository import save_observation
from app.models import (
    AssetType,
    AvailabilityStatus,
    Facility,
    FacilityPage,
    Listing,
    ParseStatus,
    PriceUnit,
    Unit,
    facility_page_from_parse,
)
from app.providers.storquest.parser import parse_facility_page

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRACY_FIXTURE = (
    Path(__file__).parent
    / "fixtures"
    / "storquest"
    / "tracy-ca-225-gandy-dancer-drive.html"
)
TRACY_URL = "https://www.storquest.com/self-storage/ca/tracy/225-gandy-dancer-drive"
TRACY_SLUG = "tracy-ca-225-gandy-dancer-drive"


def _test_database_url() -> str | None:
    explicit = os.getenv("TEST_DATABASE_URL", "").strip()
    if explicit:
        return explicit
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        return None
    return make_url(url).set(database="storage_market_data_test").render_as_string(
        hide_password=False
    )


def _ensure_database(url: str) -> None:
    parsed = make_url(url)
    db_name = parsed.database
    if not db_name:
        raise RuntimeError("test database URL has no database name")
    admin = parsed.set(database="postgres")
    engine = create_engine(admin, isolation_level="AUTOCOMMIT", future=True)
    with engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :n"),
            {"n": db_name},
        ).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    engine.dispose()


@pytest.fixture(scope="session")
def engine() -> Engine:
    url = _test_database_url()
    if not url:
        pytest.skip("TEST_DATABASE_URL / DATABASE_URL not set")
    _ensure_database(url)
    eng = create_engine(url, future=True)
    yield eng
    eng.dispose()


@pytest.fixture
def session(engine: Engine) -> Session:
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine)


def _facility(**overrides) -> Facility:
    data = dict(
        provider="storquest",
        slug="test-facility",
        url="https://www.storquest.com/self-storage/ca/test",
        name="Test Facility",
        address="1 Main St",
    )
    data.update(overrides)
    return Facility(**data)


def _unit(**overrides) -> Unit:
    data = dict(
        provider_unit_id="unit-a",
        width_ft=5,
        length_ft=5,
        features=["Ground-Level Access"],
        standard_price=84,
        promo_price=37,
        availability_status=AvailabilityStatus.LIMITED,
        availability_text="Limited Availability",
        free_first_month=True,
    )
    data.update(overrides)
    return Unit(**data)


def _ok_page(*units: Unit, slug: str = "test-facility") -> FacilityPage:
    return FacilityPage(
        parse_status=ParseStatus.OK,
        parse_strategy="next_data_json",
        facility=_facility(slug=slug, url=f"https://example.com/{slug}"),
        units=list(units),
    )


def test_second_save_appends_observations_not_duplicates(session: Session):
    page = _ok_page(_unit(), _unit(provider_unit_id="unit-b", promo_price=42))
    t1 = datetime(2026, 8, 18, 12, 0, tzinfo=timezone.utc)
    t2 = t1 + timedelta(hours=1)

    save_observation(page, scraped_at=t1, session=session)
    save_observation(page, scraped_at=t2, session=session)
    session.flush()

    assert session.scalar(select(func.count()).select_from(FacilityRow)) == 1
    assert session.scalar(select(func.count()).select_from(UnitRow)) == 2
    observations = session.scalars(
        select(ObservationRow).order_by(ObservationRow.scraped_at)
    ).all()
    assert len(observations) == 4
    timestamps = {row.scraped_at for row in observations}
    assert timestamps == {t1, t2}


def test_failed_scrape_does_not_write_sold_out(session: Session):
    t = datetime(2026, 8, 18, 12, 0, tzinfo=timezone.utc)
    failed = FacilityPage(
        parse_status=ParseStatus.FAILED,
        parse_strategy=None,
        facility=_facility(slug="failed"),
        units=[],
    )
    empty = FacilityPage(
        parse_status=ParseStatus.NO_UNITS,
        parse_strategy="next_data_json",
        facility=_facility(slug="empty", url="https://example.com/empty"),
        units=[],
    )

    save_observation(failed, scraped_at=t, session=session)
    save_observation(empty, scraped_at=t, session=session)
    session.flush()

    assert session.scalar(select(func.count()).select_from(FacilityRow)) == 0
    assert session.scalar(select(func.count()).select_from(UnitRow)) == 0
    assert session.scalar(select(func.count()).select_from(ObservationRow)) == 0


def test_alembic_creates_core_tables(engine: Engine):
    from alembic import command
    from alembic.config import Config

    Base.metadata.drop_all(engine)
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS alembic_version"))

    cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
    cfg.set_main_option(
        "sqlalchemy.url", engine.url.render_as_string(hide_password=False)
    )
    command.upgrade(cfg, "head")

    tables = set(inspect(engine).get_table_names())
    assert {"facilities", "units", "observations"}.issubset(tables)
    facility_cols = {col["name"] for col in inspect(engine).get_columns("facilities")}
    unit_cols = {col["name"] for col in inspect(engine).get_columns("units")}
    obs_cols = {col["name"] for col in inspect(engine).get_columns("observations")}
    assert {"asset_type", "attributes"}.issubset(facility_cols)
    assert {"square_footage", "attributes", "price_data_available"}.issubset(unit_cols)
    assert {"price", "price_unit", "price_data_available"}.issubset(obs_cols)
    Base.metadata.drop_all(engine)


def test_alembic_backfills_existing_storquest_rows(engine: Engine):
    from alembic import command
    from alembic.config import Config

    Base.metadata.drop_all(engine)
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS alembic_version"))

    cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
    cfg.set_main_option(
        "sqlalchemy.url", engine.url.render_as_string(hide_password=False)
    )
    command.upgrade(cfg, "001_initial")

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO facilities (provider, slug, url, name)
                VALUES ('storquest', 'tracy-backfill', 'https://example.com/tracy-backfill', 'Tracy')
                """
            )
        )
        facility_id = conn.execute(
            text("SELECT id FROM facilities WHERE slug = 'tracy-backfill'")
        ).scalar()
        conn.execute(
            text(
                """
                INSERT INTO units (
                    facility_id, identity_key, provider_unit_id,
                    width_ft, length_ft, features
                )
                VALUES (:fid, 'u1', 'u1', 5, 10, '[]'::jsonb)
                """
            ),
            {"fid": facility_id},
        )
        conn.execute(
            text(
                """
                INSERT INTO observations (
                    unit_id, scraped_at, standard_price, promo_price,
                    availability_status, free_first_month
                )
                SELECT id, now(), 84, 37, 'AVAILABLE', false
                FROM units WHERE identity_key = 'u1'
                """
            )
        )

    command.upgrade(cfg, "head")

    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM facilities")).scalar() == 1
        assert conn.execute(text("SELECT count(*) FROM units")).scalar() == 1
        assert conn.execute(text("SELECT count(*) FROM observations")).scalar() == 1
        assert conn.execute(
            text("SELECT asset_type FROM facilities WHERE slug = 'tracy-backfill'")
        ).scalar() == "self_storage"
        assert conn.execute(
            text("SELECT square_footage FROM units WHERE identity_key = 'u1'")
        ).scalar() == 50
        price, price_unit, available = conn.execute(
            text("SELECT price, price_unit, price_data_available FROM observations")
        ).one()
        assert price == 84
        assert price_unit == "per_unit_per_month"
        assert available is True

    Base.metadata.drop_all(engine)
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS alembic_version"))


def test_tracy_fixture_saves_twelve_units(session: Session):
    html = TRACY_FIXTURE.read_text(encoding="utf-8")
    page = facility_page_from_parse(
        parse_facility_page(html),
        provider="storquest",
        slug=TRACY_SLUG,
        url=TRACY_URL,
    )
    t = datetime(2026, 8, 18, 15, 0, tzinfo=timezone.utc)
    save_observation(page, scraped_at=t, url=TRACY_URL, session=session)
    session.flush()

    assert session.scalar(select(func.count()).select_from(FacilityRow)) == 1
    assert session.scalar(select(func.count()).select_from(UnitRow)) == 12
    assert session.scalar(select(func.count()).select_from(ObservationRow)) == 12
    facility = session.scalar(select(FacilityRow))
    assert facility is not None
    assert facility.asset_type == AssetType.SELF_STORAGE.value
    unit = session.scalar(select(UnitRow).where(UnitRow.provider_unit_id.is_not(None)))
    assert unit is not None
    assert unit.square_footage == (unit.width_ft or 0) * (unit.length_ft or 0)
    assert unit.price_data_available is True
    obs = session.scalar(select(ObservationRow))
    assert obs is not None
    assert obs.price == obs.standard_price
    assert obs.price_unit == PriceUnit.PER_UNIT_PER_MONTH.value


def test_warehouse_listing_persists_without_width_or_price(session: Session):
    page = FacilityPage(
        parse_status=ParseStatus.OK,
        parse_strategy="html_swiper",
        facility=_facility(
            provider="readyspaces",
            slug="downtown-los-angeles",
            url="https://readyspaces.com/location/los-angeles/downtown-los-angeles/",
            asset_type=AssetType.WAREHOUSE_INDUSTRIAL,
        ),
        listings=[
            Listing(
                provider_unit_id="K8",
                square_footage=1900,
                price=None,
                price_data_available=False,
                availability_status=AvailabilityStatus.AVAILABLE,
                availability_text="Now",
                attributes={"size_tier": "large"},
            )
        ],
    )
    t = datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc)
    save_observation(page, scraped_at=t, session=session)
    session.flush()

    unit = session.scalar(select(UnitRow))
    assert unit is not None
    assert unit.square_footage == 1900
    assert unit.width_ft is None
    assert unit.length_ft is None
    assert unit.price_data_available is False
    obs = session.scalar(select(ObservationRow))
    assert obs is not None
    assert obs.price is None
    assert obs.price_data_available is False
    facility = session.scalar(select(FacilityRow))
    assert facility is not None
    assert facility.asset_type == AssetType.WAREHOUSE_INDUSTRIAL.value

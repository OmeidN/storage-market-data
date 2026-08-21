from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def uses_transaction_pooler(url: str) -> bool:
    """True for PgBouncer transaction mode (Supabase pooler :6543)."""
    parsed = make_url(url)
    host = (parsed.host or "").lower()
    if parsed.port == 6543:
        return True
    return "pooler.supabase.com" in host


def create_db_engine(url: str) -> Engine:
    kwargs: dict = {"future": True, "pool_pre_ping": True}
    if uses_transaction_pooler(url):
        # psycopg3 prepared statements break PgBouncer transaction mode.
        kwargs["connect_args"] = {"prepare_threshold": None}
    return create_engine(url, **kwargs)


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        if not settings.database_url:
            raise RuntimeError(
                "DATABASE_URL is not set. Copy .env.example to .env and "
                "start Postgres with docker compose up -d."
            )
        _engine = create_db_engine(settings.database_url)
    return _engine


def session_factory() -> sessionmaker[Session]:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _SessionLocal

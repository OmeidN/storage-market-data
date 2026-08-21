"""Engine helpers for Supabase transaction pooler (no live database)."""

from app.database.engine import uses_transaction_pooler


def test_detects_transaction_pooler_port() -> None:
    url = (
        "postgresql+psycopg://postgres.ref:x@aws-0-us-west-1.pooler.supabase.com"
        ":6543/postgres?sslmode=require"
    )
    assert uses_transaction_pooler(url) is True


def test_detects_pooler_hostname_even_on_5432() -> None:
    url = (
        "postgresql+psycopg://postgres.ref:x@aws-0-us-west-1.pooler.supabase.com"
        ":5432/postgres?sslmode=require"
    )
    assert uses_transaction_pooler(url) is True


def test_local_compose_is_not_pooler() -> None:
    url = "postgresql+psycopg://storage:storage@localhost:5433/storage_market_data"
    assert uses_transaction_pooler(url) is False


def test_supabase_direct_is_not_pooler() -> None:
    url = (
        "postgresql+psycopg://postgres:x@db.example.supabase.co:5432/postgres"
        "?sslmode=require"
    )
    assert uses_transaction_pooler(url) is False

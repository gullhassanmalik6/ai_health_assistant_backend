from app.core.db_url import (
    database_ssl_connect_args,
    normalize_database_url,
    stripped_database_url,
)


def test_railway_internal_does_not_force_ssl():
    assert database_ssl_connect_args(
        "postgresql+asyncpg://u:p@postgres.railway.internal:5432/railway"
    ) == {}


def test_postgres_url_becomes_asyncpg():
    assert normalize_database_url("postgres://u:p@db.example.com:5432/app").startswith(
        "postgresql+asyncpg://"
    )
    assert "db.example.com" in stripped_database_url(
        "postgresql://u:p@db.example.com:5432/app?sslmode=require"
    )
    assert "sslmode" not in stripped_database_url(
        "postgresql+asyncpg://u:p@db.example.com:5432/app?sslmode=require"
    )

from app.core.db_url import normalize_database_url, stripped_database_url


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

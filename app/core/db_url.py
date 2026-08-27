"""Normalize hosted Postgres URLs for SQLAlchemy + asyncpg."""

from __future__ import annotations

import os
from urllib.parse import parse_qsl, quote_plus, urlencode, urlparse, urlunparse

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "db"}


def normalize_database_url(url: str) -> str:
    """Accept postgres:// / postgresql:// from Render, Railway, Neon, etc."""
    value = (url or "").strip().strip('"').strip("'")
    if not value:
        return value
    if value.startswith("sqlite"):
        return value
    if value.startswith("postgres://"):
        value = "postgresql+asyncpg://" + value[len("postgres://") :]
    elif value.startswith("postgresql://") and "+asyncpg" not in value.split("://", 1)[0]:
        value = value.replace("postgresql://", "postgresql+asyncpg://", 1)
    return value


def stripped_database_url(url: str) -> str:
    """Remove sslmode/ssl query params asyncpg does not accept in the DSN."""
    normalized = normalize_database_url(url)
    if normalized.startswith("sqlite"):
        return normalized
    parsed = urlparse(normalized)
    query = [
        (key, val)
        for key, val in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() not in {"ssl", "sslmode"}
    ]
    return urlunparse(parsed._replace(query=urlencode(query)))


def database_host(url: str) -> str:
    return (urlparse(normalize_database_url(url)).hostname or "").lower()


def is_local_database_host(url: str) -> bool:
    return database_host(url) in _LOCAL_HOSTS


def url_from_pg_env() -> str | None:
    host = os.environ.get("PGHOST")
    if not host or host.lower() in _LOCAL_HOSTS:
        return None
    user = os.environ.get("PGUSER", "postgres")
    password = os.environ.get("PGPASSWORD", "")
    port = os.environ.get("PGPORT", "5432")
    database = os.environ.get("PGDATABASE", "railway")
    return (
        f"postgresql+asyncpg://{quote_plus(user)}:{quote_plus(password)}"
        f"@{host}:{port}/{database}"
    )


def resolve_database_url(url: str) -> str:
    """If DATABASE_URL is still localhost, prefer Railway/private Postgres URLs."""
    current = stripped_database_url(normalize_database_url(url))
    if not is_local_database_host(current):
        return current
    for key in ("DATABASE_PRIVATE_URL", "DATABASE_PUBLIC_URL", "POSTGRES_URL"):
        raw = os.environ.get(key)
        if raw and not is_local_database_host(raw):
            return stripped_database_url(normalize_database_url(raw))
    built = url_from_pg_env()
    if built:
        return stripped_database_url(built)
    return current


def database_ssl_connect_args(url: str) -> dict:
    parsed = urlparse(normalize_database_url(url))
    if (parsed.scheme or "").startswith("sqlite"):
        return {}
    query = {key.lower(): val for key, val in parse_qsl(parsed.query, keep_blank_values=True)}
    sslmode = (query.get("sslmode") or query.get("ssl") or os.environ.get("DATABASE_SSL", "")).lower()
    host = (parsed.hostname or "").lower()

    if sslmode in {"disable", "false", "0"}:
        return {}
    if sslmode in {"require", "verify-ca", "verify-full", "true", "1"}:
        return {"ssl": True}
    if host in _LOCAL_HOSTS or host.endswith(".railway.internal"):
        return {}
    if any(token in host for token in ("neon.tech", "supabase.co", "amazonaws.com", "render.com")):
        return {"ssl": True}
    return {}

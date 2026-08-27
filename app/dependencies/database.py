"""Database dependency re-export so routers stay consistent."""

from app.core.database import get_db

__all__ = ["get_db"]

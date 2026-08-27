"""Liveness and readiness probes. No infrastructure details are exposed."""

from fastapi import APIRouter
from sqlalchemy import text

from app.core.database import get_session_factory
from app.utils.response import success_payload

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Liveness probe")
async def health():
    return {"status": "healthy"}


@router.get("/health/ready", summary="Readiness probe")
async def ready():
    factory = get_session_factory()
    async with factory() as session:
        await session.execute(text("SELECT 1"))
    return success_payload("Ready.", {"status": "ready", "database": "reachable"})

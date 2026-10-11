"""Notification stubs until the Notifications screen exists."""

from fastapi import APIRouter, Depends

from app.dependencies.auth import get_current_user
from app.models.user import User
from app.utils.response import success_payload

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get(
    "/unread-count",
    summary="Unread notification badge",
    description="Returns count 0 until notifications are implemented.",
)
async def unread_count(user: User = Depends(get_current_user)):
    return success_payload("Unread count retrieved.", {"count": 0})

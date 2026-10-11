"""Health tips and the daily tip card."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user
from app.dependencies.database import get_db
from app.models.user import User
from app.services.content_service import ContentService
from app.utils.response import success_payload

router = APIRouter(tags=["Health Tips"])


@router.get(
    "/health-tips/daily",
    summary="Health tip of the day",
    description="Same tip for everyone on a given calendar day. Honors X-Timezone when it is a valid IANA name.",
)
async def daily_tip(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await ContentService(db).daily_tip(request.headers.get("X-Timezone"))
    return success_payload("Daily tip retrieved.", data)


@router.get(
    "/health-tips/{tip_id}",
    summary="Health tip detail",
    description="Used by Health Tip Detail. Unknown id returns 404.",
)
async def get_health_tip(
    tip_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await ContentService(db).get_health_tip(tip_id)
    return success_payload(
        "Health tip retrieved.",
        {
            "id": item.id,
            "category": {"slug": item.category.slug, "ai_title": item.category.ai_title},
            "title": item.title,
            "subtitle": item.subtitle,
            "tint_key": item.tint_key,
            "daily_habits": item.daily_habits or [],
            "suggested_questions": item.suggested_questions or [],
        },
    )

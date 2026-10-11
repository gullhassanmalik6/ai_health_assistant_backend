"""AI doctor categories and concerns."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user
from app.dependencies.database import get_db
from app.models.user import User
from app.services.content_service import ContentService
from app.utils.response import success_payload

router = APIRouter(tags=["Categories"])


@router.get(
    "/categories",
    summary="List AI doctor categories",
    description="Home Dashboard shows the first 4. AI Doctor Categories shows all. Search is done in the app.",
)
async def list_categories(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    items = await ContentService(db).list_categories()
    return success_payload(
        "Categories retrieved.",
        {
            "items": [
                {
                    "slug": item.slug,
                    "name": item.name,
                    "icon_key": item.icon_key,
                    "tint_key": item.tint_key,
                    "sort_order": item.sort_order,
                }
                for item in items
            ]
        },
    )


@router.get(
    "/categories/{slug}",
    summary="Category detail",
    description="Used by Category Detail. Unknown slug returns 404.",
)
async def get_category(
    slug: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await ContentService(db).get_category(slug)
    return success_payload(
        "Category retrieved.",
        {
            "slug": item.slug,
            "name": item.name,
            "ai_title": item.ai_title,
            "description": item.description,
            "icon_key": item.icon_key,
            "tint_key": item.tint_key,
            "concerns": [
                {
                    "id": concern.id,
                    "title": concern.title,
                    "subtitle": concern.subtitle,
                    "tint_key": concern.tint_key,
                }
                for concern in item.concerns
            ],
            "health_tips": [
                {
                    "id": tip.id,
                    "title": tip.title,
                    "subtitle": tip.subtitle,
                    "tint_key": tip.tint_key,
                }
                for tip in item.health_tips
            ],
        },
    )


@router.get(
    "/concerns/{concern_id}",
    summary="Concern detail",
    description="Used by Concern Detail. Unknown id returns 404.",
)
async def get_concern(
    concern_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await ContentService(db).get_concern(concern_id)
    return success_payload(
        "Concern retrieved.",
        {
            "id": item.id,
            "category": {"slug": item.category.slug, "ai_title": item.category.ai_title},
            "title": item.title,
            "subtitle": item.subtitle,
            "tint_key": item.tint_key,
            "symptoms": item.symptoms or [],
            "suggested_questions": item.suggested_questions or [],
        },
    )

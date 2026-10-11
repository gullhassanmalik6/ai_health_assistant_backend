"""Read-only category, concern, and health-tip catalog."""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.data.seed_content import (
    CATEGORIES,
    CONCERNS,
    DAILY_TIPS,
    HEALTH_TIPS,
    category_ai_title,
    category_description,
)
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.models.content import Category, Concern, DailyTip, HealthTip

logger = get_logger(__name__)


def calendar_date_for_timezone(header: str | None) -> date:
    name = (header or "").strip() or "UTC"
    try:
        zone = ZoneInfo(name)
    except (ZoneInfoNotFoundError, Exception):
        zone = ZoneInfo("UTC")
    return datetime.now(zone).date()


class ContentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_categories(self) -> list[Category]:
        result = await self.session.execute(select(Category).order_by(Category.sort_order.asc()))
        return list(result.scalars().all())

    async def get_category(self, slug: str) -> Category:
        result = await self.session.execute(
            select(Category)
            .options(selectinload(Category.concerns), selectinload(Category.health_tips))
            .where(Category.slug == slug)
        )
        category = result.scalar_one_or_none()
        if category is None:
            raise NotFoundError("Category not found.")
        return category

    async def get_concern(self, concern_id: str) -> Concern:
        result = await self.session.execute(
            select(Concern).options(selectinload(Concern.category)).where(Concern.id == concern_id)
        )
        item = result.scalar_one_or_none()
        if item is None:
            raise NotFoundError("Concern not found.")
        return item

    async def get_health_tip(self, tip_id: str) -> HealthTip:
        result = await self.session.execute(
            select(HealthTip).options(selectinload(HealthTip.category)).where(HealthTip.id == tip_id)
        )
        item = result.scalar_one_or_none()
        if item is None:
            raise NotFoundError("Health tip not found.")
        return item

    async def daily_tip(self, timezone_header: str | None) -> dict:
        today = calendar_date_for_timezone(timezone_header)
        result = await self.session.execute(select(DailyTip).order_by(DailyTip.sort_order.asc()))
        pool = list(result.scalars().all())
        if not pool:
            text = DAILY_TIPS[0]
        else:
            index = today.toordinal() % len(pool)
            text = pool[index].text
        return {"date": today.isoformat(), "text": text}


async def seed_content_if_empty(session: AsyncSession) -> None:
    existing = await session.execute(select(Category).limit(1))
    if existing.scalar_one_or_none() is not None:
        return

    for item in CATEGORIES:
        session.add(
            Category(
                slug=item["slug"],
                name=item["name"],
                ai_title=category_ai_title(item["name"]),
                description=category_description(item["slug"], item["name"]),
                icon_key=item["slug"],
                tint_key=item["tint_key"],
                sort_order=item["sort_order"],
            )
        )
    for item in CONCERNS:
        session.add(Concern(**item))
    for item in HEALTH_TIPS:
        session.add(HealthTip(**item))
    for index, text in enumerate(DAILY_TIPS, start=1):
        session.add(DailyTip(text=text, sort_order=index))
    await session.flush()
    logger.info("Seeded AI doctor categories and health-tip catalog.")

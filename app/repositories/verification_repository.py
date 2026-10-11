"""Persistence for email verification codes."""

from __future__ import annotations

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import utcnow
from app.models.verification import EmailVerificationCode


class VerificationCodeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_active_for_user(self, user_id: uuid.UUID) -> EmailVerificationCode | None:
        result = await self.session.execute(
            select(EmailVerificationCode)
            .where(
                EmailVerificationCode.user_id == user_id,
                EmailVerificationCode.consumed_at.is_(None),
            )
            .order_by(EmailVerificationCode.sent_at.desc())
        )
        return result.scalars().first()

    async def consume_all_for_user(self, user_id: uuid.UUID) -> None:
        await self.session.execute(
            update(EmailVerificationCode)
            .where(
                EmailVerificationCode.user_id == user_id,
                EmailVerificationCode.consumed_at.is_(None),
            )
            .values(consumed_at=utcnow())
        )

    async def create(self, row: EmailVerificationCode) -> EmailVerificationCode:
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        return row

    async def save(self, row: EmailVerificationCode) -> EmailVerificationCode:
        await self.session.flush()
        await self.session.refresh(row)
        return row

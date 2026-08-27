"""Profile, allergy, condition, and medication persistence."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_profile import UserAllergy, UserCondition, UserMedication, UserProfile


class ProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_user_id(self, user_id: uuid.UUID) -> UserProfile | None:
        result = await self.session.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create(self, profile: UserProfile) -> UserProfile:
        self.session.add(profile)
        await self.session.flush()
        await self.session.refresh(profile)
        return profile

    async def save(self, profile: UserProfile) -> UserProfile:
        await self.session.flush()
        await self.session.refresh(profile)
        return profile

    async def delete(self, profile: UserProfile) -> None:
        await self.session.delete(profile)
        await self.session.flush()


class AllergyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_user(self, user_id: uuid.UUID) -> list[UserAllergy]:
        result = await self.session.execute(
            select(UserAllergy)
            .where(UserAllergy.user_id == user_id)
            .order_by(UserAllergy.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_owned(self, allergy_id: uuid.UUID, user_id: uuid.UUID) -> UserAllergy | None:
        result = await self.session.execute(
            select(UserAllergy).where(
                UserAllergy.id == allergy_id,
                UserAllergy.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, allergy: UserAllergy) -> UserAllergy:
        self.session.add(allergy)
        await self.session.flush()
        await self.session.refresh(allergy)
        return allergy

    async def save(self, allergy: UserAllergy) -> UserAllergy:
        await self.session.flush()
        await self.session.refresh(allergy)
        return allergy

    async def delete(self, allergy: UserAllergy) -> None:
        await self.session.delete(allergy)
        await self.session.flush()

    async def delete_all_for_user(self, user_id: uuid.UUID) -> None:
        items = await self.list_for_user(user_id)
        for item in items:
            await self.session.delete(item)
        await self.session.flush()


class ConditionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_user(self, user_id: uuid.UUID) -> list[UserCondition]:
        result = await self.session.execute(
            select(UserCondition)
            .where(UserCondition.user_id == user_id)
            .order_by(UserCondition.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_owned(self, condition_id: uuid.UUID, user_id: uuid.UUID) -> UserCondition | None:
        result = await self.session.execute(
            select(UserCondition).where(
                UserCondition.id == condition_id,
                UserCondition.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, condition: UserCondition) -> UserCondition:
        self.session.add(condition)
        await self.session.flush()
        await self.session.refresh(condition)
        return condition

    async def save(self, condition: UserCondition) -> UserCondition:
        await self.session.flush()
        await self.session.refresh(condition)
        return condition

    async def delete(self, condition: UserCondition) -> None:
        await self.session.delete(condition)
        await self.session.flush()

    async def delete_all_for_user(self, user_id: uuid.UUID) -> None:
        items = await self.list_for_user(user_id)
        for item in items:
            await self.session.delete(item)
        await self.session.flush()


class MedicationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_user(self, user_id: uuid.UUID) -> list[UserMedication]:
        result = await self.session.execute(
            select(UserMedication)
            .where(UserMedication.user_id == user_id)
            .order_by(UserMedication.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_owned(self, medication_id: uuid.UUID, user_id: uuid.UUID) -> UserMedication | None:
        result = await self.session.execute(
            select(UserMedication).where(
                UserMedication.id == medication_id,
                UserMedication.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, medication: UserMedication) -> UserMedication:
        self.session.add(medication)
        await self.session.flush()
        await self.session.refresh(medication)
        return medication

    async def save(self, medication: UserMedication) -> UserMedication:
        await self.session.flush()
        await self.session.refresh(medication)
        return medication

    async def delete(self, medication: UserMedication) -> None:
        await self.session.delete(medication)
        await self.session.flush()

    async def delete_all_for_user(self, user_id: uuid.UUID) -> None:
        items = await self.list_for_user(user_id)
        for item in items:
            await self.session.delete(item)
        await self.session.flush()

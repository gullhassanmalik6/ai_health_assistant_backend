"""Profile, completion scoring, and owned health-record CRUD."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    BLOOD_GROUP_UNKNOWN_COUNTS_AS_FILLED,
    HEALTH_LIST_MAX_ITEMS,
    HEALTH_LIST_NAME_MAX_LENGTH,
    MAX_AGE_YEARS_PERSONAL,
    PROFILE_COMPLETION_COUNT_ALLERGIES,
    PROFILE_COMPLETION_COUNT_CONDITIONS,
    PROFILE_COMPLETION_COUNT_PHOTO,
    PROFILE_COMPLETION_FIELDS,
    AllergySeverity,
    BloodGroup,
    ConditionStatus,
    HeightUnit,
    MedicationRoute,
    WeightUnit,
)
from app.core.exceptions import NotFoundError, ValidationAppError
from app.models.user import User
from app.models.user_profile import UserAllergy, UserCondition, UserMedication, UserProfile
from app.repositories.profile_repository import (
    AllergyRepository,
    ConditionRepository,
    MedicationRepository,
    ProfileRepository,
)
from app.repositories.user_repository import UserRepository
from app.utils.validators import (
    height_to_cm,
    validate_date_of_birth,
    validate_height,
    validate_phone_number,
    validate_weight,
    weight_to_kg,
)


class ProfileService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.profiles = ProfileRepository(session)
        self.allergies = AllergyRepository(session)
        self.conditions = ConditionRepository(session)
        self.medications = MedicationRepository(session)

    async def get_or_create_profile(self, user: User) -> UserProfile:
        profile = await self.profiles.get_by_user_id(user.id)
        if profile is None:
            profile = await self.profiles.create(UserProfile(user_id=user.id))
        return profile

    async def update_profile(self, user: User, payload: dict[str, Any], *, partial: bool) -> User:
        profile = await self.get_or_create_profile(user)

        if "name" in payload:
            name = payload["name"]
            user.name = name.strip() if name else None
        elif not partial:
            # PUT replaces identity name only when provided; absence leaves it.
            pass

        self._apply_profile_fields(profile, payload, partial=partial)
        await self.users.save(user)
        await self.profiles.save(profile)
        loaded = await self.users.get_by_id(user.id)
        return loaded or user

    async def reset_profile(self, user: User) -> User:
        """Clear health profile data. Does not delete the account."""
        profile = await self.get_or_create_profile(user)
        profile.gender = None
        profile.date_of_birth = None
        profile.height_value = None
        profile.height_unit = None
        profile.height_cm = None
        profile.weight_value = None
        profile.weight_unit = None
        profile.weight_kg = None
        profile.blood_group = None
        profile.emergency_contact_name = None
        profile.emergency_contact_phone = None
        profile.profile_photo_url = None
        profile.profile_photo_key = None
        await self.profiles.save(profile)
        await self.allergies.delete_all_for_user(user.id)
        await self.conditions.delete_all_for_user(user.id)
        await self.medications.delete_all_for_user(user.id)
        loaded = await self.users.get_by_id(user.id)
        return loaded or user

    def completion(self, user: User) -> dict[str, Any]:
        profile = user.profile
        blood_group = profile.blood_group if profile else None
        blood_filled = bool(blood_group) and (
            BLOOD_GROUP_UNKNOWN_COUNTS_AS_FILLED or blood_group != BloodGroup.UNKNOWN
        )
        checks = {
            "name": bool(user.name and user.name.strip()),
            "gender": bool(profile and profile.gender),
            "date_of_birth": bool(profile and profile.date_of_birth),
            "height": bool(profile and profile.height_value is not None and profile.height_unit),
            "weight": bool(profile and profile.weight_value is not None and profile.weight_unit),
            "blood_group": blood_filled,
            "profile_photo": bool(profile and (profile.profile_photo_key or profile.profile_photo_url)),
            "allergies": bool(user.allergies),
            "conditions": bool(user.conditions),
        }
        fields = list(PROFILE_COMPLETION_FIELDS)
        if PROFILE_COMPLETION_COUNT_PHOTO and "profile_photo" not in fields:
            fields.append("profile_photo")
        if PROFILE_COMPLETION_COUNT_ALLERGIES and "allergies" not in fields:
            fields.append("allergies")
        if PROFILE_COMPLETION_COUNT_CONDITIONS and "conditions" not in fields:
            fields.append("conditions")
        completed = [field for field in fields if checks[field]]
        missing = [field for field in fields if not checks[field]]
        total = len(fields)
        percentage = int(round((len(completed) / total) * 100)) if total else 0
        return {
            "percentage": percentage,
            "is_complete": percentage == 100,
            "completed": completed,
            "missing": missing,
        }

    def _apply_profile_fields(
        self,
        profile: UserProfile,
        payload: dict[str, Any],
        *,
        partial: bool,
    ) -> None:
        def assigned(key: str) -> bool:
            return key in payload if partial else True

        if assigned("gender"):
            gender = payload.get("gender")
            profile.gender = gender.value if hasattr(gender, "value") else gender

        if assigned("date_of_birth"):
            dob = payload.get("date_of_birth")
            profile.date_of_birth = validate_date_of_birth(dob) if dob else None

        if assigned("height"):
            height = payload.get("height")
            if height:
                unit = HeightUnit(height["unit"] if isinstance(height, dict) else height.unit)
                value = float(height["value"] if isinstance(height, dict) else height.value)
                validate_height(value, unit)
                profile.height_value = value
                profile.height_unit = unit.value
                profile.height_cm = height_to_cm(value, unit)
            else:
                profile.height_value = None
                profile.height_unit = None
                profile.height_cm = None

        if assigned("weight"):
            weight = payload.get("weight")
            if weight:
                unit = WeightUnit(weight["unit"] if isinstance(weight, dict) else weight.unit)
                value = float(weight["value"] if isinstance(weight, dict) else weight.value)
                validate_weight(value, unit)
                profile.weight_value = value
                profile.weight_unit = unit.value
                profile.weight_kg = weight_to_kg(value, unit)
            else:
                profile.weight_value = None
                profile.weight_unit = None
                profile.weight_kg = None

        if assigned("blood_group"):
            blood = payload.get("blood_group")
            profile.blood_group = blood.value if hasattr(blood, "value") else blood

        if assigned("emergency_contact_name"):
            name = payload.get("emergency_contact_name")
            profile.emergency_contact_name = name.strip() if name else None

        if assigned("emergency_contact_phone"):
            phone = payload.get("emergency_contact_phone")
            profile.emergency_contact_phone = validate_phone_number(phone) if phone else None

        if assigned("profile_photo_url"):
            profile.profile_photo_url = payload.get("profile_photo_url")

    async def update_personal(self, user: User, payload: dict[str, Any]) -> User:
        profile = await self.get_or_create_profile(user)
        if "name" in payload:
            name = payload["name"]
            if name is None or not str(name).strip():
                raise ValidationAppError(
                    "Please check the highlighted fields.",
                    details={"name": "Enter your full name"},
                )
            user.name = str(name).strip()
        if "date_of_birth" in payload:
            dob = payload.get("date_of_birth")
            profile.date_of_birth = (
                validate_date_of_birth(dob, max_age=MAX_AGE_YEARS_PERSONAL, field="date_of_birth") if dob else None
            )
        if "gender" in payload:
            gender = payload.get("gender")
            profile.gender = gender.value if hasattr(gender, "value") else gender
        await self.users.save(user)
        await self.profiles.save(profile)
        loaded = await self.users.get_by_id(user.id)
        return loaded or user

    async def update_health(self, user: User, payload: dict[str, Any]) -> User:
        profile = await self.get_or_create_profile(user)
        health_fields = {key: payload[key] for key in ("height", "weight", "blood_group") if key in payload}
        if health_fields:
            self._apply_profile_fields(profile, health_fields, partial=True)
            await self.profiles.save(profile)
        if "allergies" in payload:
            await self.replace_allergy_names(user, payload["allergies"] or [])
        if "conditions" in payload:
            await self.replace_condition_names(user, payload["conditions"] or [])
        await self.session.flush()
        await self.session.refresh(user, attribute_names=["profile", "allergies", "conditions"])
        loaded = await self.users.get_by_id(user.id)
        return loaded or user

    def _normalize_health_names(self, names: list[str], *, field: str) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for raw in names:
            cleaned = (raw or "").strip()
            if not cleaned:
                raise ValidationAppError(
                    "Please check the highlighted fields.",
                    details={field: "Enter a name"},
                )
            if len(cleaned) > HEALTH_LIST_NAME_MAX_LENGTH:
                raise ValidationAppError(
                    "Please check the highlighted fields.",
                    details={field: "Each name must be 100 characters or fewer"},
                )
            key = cleaned.lower()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(cleaned)
        if len(normalized) > HEALTH_LIST_MAX_ITEMS:
            raise ValidationAppError(
                "Please check the highlighted fields.",
                details={field: "You can add at most 50 items"},
            )
        return normalized

    async def replace_allergy_names(self, user: User, names: list[str]) -> None:
        normalized = self._normalize_health_names(names, field="allergies")
        existing = await self.allergies.list_for_user(user.id)
        by_key = {item.allergy_name.lower(): item for item in existing}
        keep_ids: set[uuid.UUID] = set()
        for index, name in enumerate(normalized):
            current = by_key.get(name.lower())
            if current is not None:
                current.allergy_name = name
                current.sort_order = index
                await self.allergies.save(current)
                keep_ids.add(current.id)
            else:
                created = await self.allergies.create(
                    UserAllergy(
                        user_id=user.id,
                        allergy_name=name,
                        severity=AllergySeverity.UNKNOWN.value,
                        sort_order=index,
                    )
                )
                keep_ids.add(created.id)
        for item in existing:
            if item.id not in keep_ids:
                await self.allergies.delete(item)

    async def replace_condition_names(self, user: User, names: list[str]) -> None:
        normalized = self._normalize_health_names(names, field="conditions")
        existing = await self.conditions.list_for_user(user.id)
        by_key = {item.condition_name.lower(): item for item in existing}
        keep_ids: set[uuid.UUID] = set()
        for index, name in enumerate(normalized):
            current = by_key.get(name.lower())
            if current is not None:
                current.condition_name = name
                current.sort_order = index
                await self.conditions.save(current)
                keep_ids.add(current.id)
            else:
                created = await self.conditions.create(
                    UserCondition(
                        user_id=user.id,
                        condition_name=name,
                        status=None,
                        sort_order=index,
                    )
                )
                keep_ids.add(created.id)
        for item in existing:
            if item.id not in keep_ids:
                await self.conditions.delete(item)

    async def create_allergy(self, user: User, data: dict[str, Any]) -> UserAllergy:
        existing = await self.allergies.list_for_user(user.id)
        fields = self._allergy_fields(data)
        fields["sort_order"] = len(existing)
        allergy = UserAllergy(user_id=user.id, **fields)
        return await self.allergies.create(allergy)

    async def list_allergies(self, user: User) -> list[UserAllergy]:
        return await self.allergies.list_for_user(user.id)

    async def update_allergy(self, user: User, allergy_id: uuid.UUID, data: dict[str, Any]) -> UserAllergy:
        allergy = await self.allergies.get_owned(allergy_id, user.id)
        if allergy is None:
            raise NotFoundError("Allergy not found.")
        for key, value in self._allergy_fields(data, partial=True).items():
            setattr(allergy, key, value)
        return await self.allergies.save(allergy)

    async def delete_allergy(self, user: User, allergy_id: uuid.UUID) -> None:
        allergy = await self.allergies.get_owned(allergy_id, user.id)
        if allergy is None:
            raise NotFoundError("Allergy not found.")
        await self.allergies.delete(allergy)

    async def create_condition(self, user: User, data: dict[str, Any]) -> UserCondition:
        existing = await self.conditions.list_for_user(user.id)
        fields = self._condition_fields(data)
        fields["sort_order"] = len(existing)
        condition = UserCondition(user_id=user.id, **fields)
        return await self.conditions.create(condition)

    async def list_conditions(self, user: User) -> list[UserCondition]:
        return await self.conditions.list_for_user(user.id)

    async def update_condition(
        self, user: User, condition_id: uuid.UUID, data: dict[str, Any]
    ) -> UserCondition:
        condition = await self.conditions.get_owned(condition_id, user.id)
        if condition is None:
            raise NotFoundError("Condition not found.")
        for key, value in self._condition_fields(data, partial=True).items():
            setattr(condition, key, value)
        return await self.conditions.save(condition)

    async def delete_condition(self, user: User, condition_id: uuid.UUID) -> None:
        condition = await self.conditions.get_owned(condition_id, user.id)
        if condition is None:
            raise NotFoundError("Condition not found.")
        await self.conditions.delete(condition)

    async def create_medication(self, user: User, data: dict[str, Any]) -> UserMedication:
        medication = UserMedication(user_id=user.id, **self._medication_fields(data))
        return await self.medications.create(medication)

    async def list_medications(self, user: User) -> list[UserMedication]:
        return await self.medications.list_for_user(user.id)

    async def update_medication(
        self, user: User, medication_id: uuid.UUID, data: dict[str, Any]
    ) -> UserMedication:
        medication = await self.medications.get_owned(medication_id, user.id)
        if medication is None:
            raise NotFoundError("Medication not found.")
        for key, value in self._medication_fields(data, partial=True).items():
            setattr(medication, key, value)
        return await self.medications.save(medication)

    async def delete_medication(self, user: User, medication_id: uuid.UUID) -> None:
        medication = await self.medications.get_owned(medication_id, user.id)
        if medication is None:
            raise NotFoundError("Medication not found.")
        await self.medications.delete(medication)

    def _allergy_fields(self, data: dict[str, Any], *, partial: bool = False) -> dict[str, Any]:
        fields: dict[str, Any] = {}
        if "allergy_name" in data or not partial:
            fields["allergy_name"] = data["allergy_name"].strip()
        if "reaction" in data or not partial:
            reaction = data.get("reaction")
            fields["reaction"] = reaction.strip() if reaction else None
        if "severity" in data or not partial:
            severity = data.get("severity") or AllergySeverity.UNKNOWN
            fields["severity"] = severity.value if hasattr(severity, "value") else severity
        if "notes" in data or not partial:
            notes = data.get("notes")
            fields["notes"] = notes.strip() if notes else None
        return fields

    def _condition_fields(self, data: dict[str, Any], *, partial: bool = False) -> dict[str, Any]:
        fields: dict[str, Any] = {}
        if "condition_name" in data or not partial:
            fields["condition_name"] = data["condition_name"].strip()
        if "diagnosed_date" in data or not partial:
            diagnosed: date | None = data.get("diagnosed_date")
            if diagnosed and diagnosed > date.today():
                from app.core.exceptions import ValidationAppError

                raise ValidationAppError("Diagnosed date cannot be in the future.")
            fields["diagnosed_date"] = diagnosed
        if "status" in data or not partial:
            status = data.get("status") or ConditionStatus.ACTIVE
            fields["status"] = status.value if hasattr(status, "value") else status
        if "notes" in data or not partial:
            notes = data.get("notes")
            fields["notes"] = notes.strip() if notes else None
        return fields

    def _medication_fields(self, data: dict[str, Any], *, partial: bool = False) -> dict[str, Any]:
        fields: dict[str, Any] = {}
        if "medication_name" in data or not partial:
            fields["medication_name"] = data["medication_name"].strip()
        if "dosage" in data or not partial:
            dosage = data.get("dosage")
            fields["dosage"] = dosage.strip() if dosage else None
        if "frequency" in data or not partial:
            frequency = data.get("frequency")
            fields["frequency"] = frequency.strip() if frequency else None
        if "route" in data or not partial:
            route = data.get("route")
            fields["route"] = route.value if hasattr(route, "value") else route
        if "notes" in data or not partial:
            notes = data.get("notes")
            fields["notes"] = notes.strip() if notes else None
        return fields

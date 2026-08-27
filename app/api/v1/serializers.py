"""Map domain objects to API payloads. Routers stay thin."""

from __future__ import annotations

from app.api.v1.auth.schemas import AuthData, AuthUserPayload, TokenPayload
from app.api.v1.profile.schemas import (
    AllergyData,
    ConditionData,
    HeightMeasurement,
    MedicationData,
    ProfileCompletionData,
    ProfileData,
    WeightMeasurement,
)
from app.api.v1.users.schemas import UserMeData
from app.core.firebase import FirebaseSession
from app.models.user import User
from app.services.profile_service import ProfileService


def user_me_payload(user: User, completion: dict) -> UserMeData:
    return UserMeData(
        id=str(user.id),
        firebase_uid=user.firebase_uid,
        email=user.email,
        name=user.name,
        auth_provider=user.auth_provider,
        is_guest=user.is_guest,
        is_active=user.is_active,
        email_verified=user.email_verified,
        onboarding_completed=user.onboarding_completed,
        profile_completed=completion["is_complete"],
        profile_completion_percentage=completion["percentage"],
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


def auth_user_payload(user: User, completion: dict) -> AuthUserPayload:
    return AuthUserPayload(
        id=str(user.id),
        firebase_uid=user.firebase_uid,
        email=user.email,
        name=user.name,
        auth_provider=user.auth_provider,
        is_guest=user.is_guest,
        email_verified=user.email_verified,
        onboarding_completed=user.onboarding_completed,
        profile_completion_percentage=completion["percentage"],
        profile_completed=completion["is_complete"],
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


def token_payload(session: FirebaseSession | None) -> TokenPayload | None:
    if session is None or not session.id_token:
        return None
    return TokenPayload(
        id_token=session.id_token,
        refresh_token=session.refresh_token,
        expires_in=session.expires_in,
        token_type="Bearer",
    )


def auth_data(user: User, session: FirebaseSession | None, completion: dict) -> AuthData:
    return AuthData(
        user=auth_user_payload(user, completion),
        tokens=token_payload(session),
        is_guest=user.is_guest,
        email_verified=user.email_verified,
        profile_completed=completion["is_complete"],
    )


def profile_payload(user: User, completion: dict) -> ProfileData:
    profile = user.profile
    height = None
    weight = None
    if profile and profile.height_value is not None and profile.height_unit:
        height = HeightMeasurement(value=profile.height_value, unit=profile.height_unit)
    if profile and profile.weight_value is not None and profile.weight_unit:
        weight = WeightMeasurement(value=profile.weight_value, unit=profile.weight_unit)

    return ProfileData(
        id=str(profile.id) if profile else str(user.id),
        user_id=str(user.id),
        name=user.name,
        email=user.email,
        gender=profile.gender if profile else None,
        date_of_birth=profile.date_of_birth if profile else None,
        height=height,
        weight=weight,
        blood_group=profile.blood_group if profile else None,
        emergency_contact_name=profile.emergency_contact_name if profile else None,
        emergency_contact_phone=profile.emergency_contact_phone if profile else None,
        profile_photo_url=profile.profile_photo_url if profile else None,
        onboarding_completed=user.onboarding_completed,
        profile_completed=completion["is_complete"],
        profile_completion_percentage=completion["percentage"],
        allergies=[AllergyData.model_validate(item) for item in (user.allergies or [])],
        conditions=[ConditionData.model_validate(item) for item in (user.conditions or [])],
        medications=[MedicationData.model_validate(item) for item in (user.medications or [])],
        created_at=profile.created_at if profile else user.created_at,
        updated_at=profile.updated_at if profile else user.updated_at,
    )


def completion_payload(completion: dict) -> ProfileCompletionData:
    return ProfileCompletionData(
        percentage=completion["percentage"],
        is_complete=completion["is_complete"],
        completed=completion["completed"],
        missing=completion["missing"],
    )


def compute_completion(user: User) -> dict:
    return ProfileService.__new__(ProfileService).completion(user)

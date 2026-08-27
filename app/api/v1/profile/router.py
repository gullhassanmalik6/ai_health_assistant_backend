"""Profile and structured health-history endpoints. Ownership is always the authenticated user."""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.profile.schemas import (
    AllergyData,
    AllergyPatchRequest,
    AllergyWriteRequest,
    ConditionData,
    ConditionPatchRequest,
    ConditionWriteRequest,
    MedicationData,
    MedicationPatchRequest,
    MedicationWriteRequest,
    ProfilePatchRequest,
    ProfilePutRequest,
)
from app.api.v1.serializers import completion_payload, compute_completion, profile_payload
from app.dependencies.auth import get_current_user
from app.dependencies.database import get_db
from app.models.user import User
from app.services.profile_service import ProfileService
from app.utils.response import success_payload

router = APIRouter(prefix="/profile", tags=["Profile"])


def _reload_payload(user: User, message: str):
    completion = compute_completion(user)
    return success_payload(message, profile_payload(user, completion).model_dump(mode="json"))


@router.get(
    "",
    summary="Get the complete current profile",
)
async def get_profile(user: User = Depends(get_current_user)):
    return _reload_payload(user, "Profile retrieved.")


@router.put(
    "",
    summary="Replace editable profile fields",
    description="Omitted optional fields are cleared. Nested allergies/conditions/medications are managed via their own endpoints.",
)
async def put_profile(
    body: ProfilePutRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    updated = await ProfileService(db).update_profile(
        user,
        body.model_dump(exclude_unset=False),
        partial=False,
    )
    return _reload_payload(updated, "Profile updated successfully.")


@router.patch(
    "",
    summary="Partially update the profile",
)
async def patch_profile(
    body: ProfilePatchRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    updated = await ProfileService(db).update_profile(
        user,
        body.model_dump(exclude_unset=True),
        partial=True,
    )
    return _reload_payload(updated, "Profile updated successfully.")


@router.delete(
    "",
    summary="Reset the health profile",
    description="Clears profile fields and related allergies, conditions, and medications. Does not delete the account. Use DELETE /api/v1/users/me for account deletion.",
)
async def reset_profile(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    updated = await ProfileService(db).reset_profile(user)
    return _reload_payload(updated, "Profile reset successfully.")


@router.get(
    "/completion",
    summary="Profile completion score",
    description="Backend-calculated. Flutter must not hardcode this logic.",
    tags=["Profile"],
)
async def profile_completion(user: User = Depends(get_current_user)):
    completion = compute_completion(user)
    return success_payload(
        "Profile completion retrieved.",
        completion_payload(completion).model_dump(),
    )


# --- Allergies ----------------------------------------------------------------


@router.get("/allergies", summary="List allergies", tags=["Allergies"])
async def list_allergies(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    items = await ProfileService(db).list_allergies(user)
    return success_payload(
        "Allergies retrieved.",
        [AllergyData.model_validate(item).model_dump(mode="json") for item in items],
    )


@router.post(
    "/allergies",
    status_code=status.HTTP_201_CREATED,
    summary="Create an allergy",
    tags=["Allergies"],
)
async def create_allergy(
    body: AllergyWriteRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await ProfileService(db).create_allergy(user, body.model_dump())
    return JSONResponse(
        status_code=201,
        content=success_payload(
            "Allergy created.",
            AllergyData.model_validate(item).model_dump(mode="json"),
        ),
    )


@router.put("/allergies/{allergy_id}", summary="Replace an allergy", tags=["Allergies"])
async def update_allergy(
    allergy_id: UUID,
    body: AllergyWriteRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await ProfileService(db).update_allergy(user, allergy_id, body.model_dump())
    return success_payload(
        "Allergy updated.",
        AllergyData.model_validate(item).model_dump(mode="json"),
    )


@router.patch("/allergies/{allergy_id}", summary="Partially update an allergy", tags=["Allergies"])
async def patch_allergy(
    allergy_id: UUID,
    body: AllergyPatchRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await ProfileService(db).update_allergy(
        user, allergy_id, body.model_dump(exclude_unset=True)
    )
    return success_payload(
        "Allergy updated.",
        AllergyData.model_validate(item).model_dump(mode="json"),
    )


@router.delete("/allergies/{allergy_id}", summary="Delete an allergy", tags=["Allergies"])
async def delete_allergy(
    allergy_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await ProfileService(db).delete_allergy(user, allergy_id)
    return success_payload("Allergy deleted.", None)


# --- Conditions ---------------------------------------------------------------


@router.get("/conditions", summary="List medical conditions", tags=["Conditions"])
async def list_conditions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    items = await ProfileService(db).list_conditions(user)
    return success_payload(
        "Conditions retrieved.",
        [ConditionData.model_validate(item).model_dump(mode="json") for item in items],
    )


@router.post(
    "/conditions",
    status_code=status.HTTP_201_CREATED,
    summary="Create a medical condition",
    tags=["Conditions"],
)
async def create_condition(
    body: ConditionWriteRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await ProfileService(db).create_condition(user, body.model_dump())
    return JSONResponse(
        status_code=201,
        content=success_payload(
            "Condition created.",
            ConditionData.model_validate(item).model_dump(mode="json"),
        ),
    )


@router.put("/conditions/{condition_id}", summary="Replace a condition", tags=["Conditions"])
async def update_condition(
    condition_id: UUID,
    body: ConditionWriteRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await ProfileService(db).update_condition(user, condition_id, body.model_dump())
    return success_payload(
        "Condition updated.",
        ConditionData.model_validate(item).model_dump(mode="json"),
    )


@router.patch("/conditions/{condition_id}", summary="Partially update a condition", tags=["Conditions"])
async def patch_condition(
    condition_id: UUID,
    body: ConditionPatchRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await ProfileService(db).update_condition(
        user, condition_id, body.model_dump(exclude_unset=True)
    )
    return success_payload(
        "Condition updated.",
        ConditionData.model_validate(item).model_dump(mode="json"),
    )


@router.delete("/conditions/{condition_id}", summary="Delete a condition", tags=["Conditions"])
async def delete_condition(
    condition_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await ProfileService(db).delete_condition(user, condition_id)
    return success_payload("Condition deleted.", None)


# --- Medications --------------------------------------------------------------


@router.get(
    "/medications",
    summary="List current medications",
    description="User medication profile only. Prescription analysis belongs to a later phase.",
    tags=["Medications"],
)
async def list_medications(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    items = await ProfileService(db).list_medications(user)
    return success_payload(
        "Medications retrieved.",
        [MedicationData.model_validate(item).model_dump(mode="json") for item in items],
    )


@router.post(
    "/medications",
    status_code=status.HTTP_201_CREATED,
    summary="Create a current medication",
    tags=["Medications"],
)
async def create_medication(
    body: MedicationWriteRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await ProfileService(db).create_medication(user, body.model_dump())
    return JSONResponse(
        status_code=201,
        content=success_payload(
            "Medication created.",
            MedicationData.model_validate(item).model_dump(mode="json"),
        ),
    )


@router.put("/medications/{medication_id}", summary="Replace a medication", tags=["Medications"])
async def update_medication(
    medication_id: UUID,
    body: MedicationWriteRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await ProfileService(db).update_medication(user, medication_id, body.model_dump())
    return success_payload(
        "Medication updated.",
        MedicationData.model_validate(item).model_dump(mode="json"),
    )


@router.patch(
    "/medications/{medication_id}",
    summary="Partially update a medication",
    tags=["Medications"],
)
async def patch_medication(
    medication_id: UUID,
    body: MedicationPatchRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await ProfileService(db).update_medication(
        user, medication_id, body.model_dump(exclude_unset=True)
    )
    return success_payload(
        "Medication updated.",
        MedicationData.model_validate(item).model_dump(mode="json"),
    )


@router.delete("/medications/{medication_id}", summary="Delete a medication", tags=["Medications"])
async def delete_medication(
    medication_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await ProfileService(db).delete_medication(user, medication_id)
    return success_payload("Medication deleted.", None)

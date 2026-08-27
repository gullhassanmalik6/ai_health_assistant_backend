"""Current-user endpoints."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.serializers import compute_completion, user_me_payload
from app.api.v1.users.schemas import UserUpdateRequest
from app.dependencies.auth import get_current_user
from app.dependencies.database import get_db
from app.models.user import User
from app.services.user_service import UserService
from app.utils.response import success_payload
from fastapi import APIRouter

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    summary="Get the current user",
    description="Identity is taken from the verified Firebase token. Do not send a user_id.",
)
async def get_me(user: User = Depends(get_current_user)):
    completion = compute_completion(user)
    return success_payload(
        "Current user retrieved.",
        user_me_payload(user, completion).model_dump(mode="json"),
    )


@router.patch(
    "/me",
    summary="Update current user display fields",
)
async def patch_me(
    body: UserUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    updated = await UserService(db).update_me(
        user,
        name=body.name,
        onboarding_completed=body.onboarding_completed,
    )
    completion = compute_completion(updated)
    return success_payload(
        "User updated successfully.",
        user_me_payload(updated, completion).model_dump(mode="json"),
    )


@router.delete(
    "/me",
    summary="Delete the current account",
    description="Removes application health data and the Firebase identity. This cannot be undone.",
)
async def delete_me(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await UserService(db).delete_account(user)
    return success_payload("Account deleted successfully.", None)

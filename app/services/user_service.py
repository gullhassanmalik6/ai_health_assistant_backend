"""Current-user and account lifecycle operations."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import firebase as firebase_auth
from app.core.exceptions import FirebaseServiceError, NotFoundError
from app.core.logging import get_logger
from app.models.user import User
from app.repositories.user_repository import UserRepository

logger = get_logger(__name__)


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)

    async def update_me(
        self,
        user: User,
        *,
        name: str | None = None,
        onboarding_completed: bool | None = None,
    ) -> User:
        if name is not None:
            user.name = name.strip()
        if onboarding_completed is not None:
            user.onboarding_completed = onboarding_completed
        await self.users.save(user)
        loaded = await self.users.get_by_id(user.id)
        return loaded or user

    async def delete_account(self, user: User) -> None:
        """Delete application data, then the Firebase identity.

        Order: dependent health rows are removed via ORM cascade / explicit
        deletes, then the user row, then Firebase. If Firebase deletion fails
        after the database commit, the identity may need a retry — the
        application record will already be gone so a subsequent login cannot
        resurrect health data.
        """
        firebase_uid = user.firebase_uid
        loaded = await self.users.get_by_id(user.id)
        if loaded is None:
            raise NotFoundError("User not found.")
        await self.users.delete(loaded)

        try:
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

        try:
            firebase_auth.delete_firebase_user(firebase_uid)
        except FirebaseServiceError:
            logger.error(
                "Application data deleted but Firebase identity removal failed. uid_present=true"
            )
            raise

    async def require_existing(self, user_id) -> User:
        user = await self.users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found.")
        return user

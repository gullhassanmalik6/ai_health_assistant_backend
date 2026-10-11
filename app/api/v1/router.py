"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1.auth.router import router as auth_router
from app.api.v1.categories.router import router as categories_router
from app.api.v1.health_tips.router import router as health_tips_router
from app.api.v1.notifications.router import router as notifications_router
from app.api.v1.profile.router import router as profile_router
from app.api.v1.users.router import router as users_router

api_v1_router = APIRouter()
api_v1_router.include_router(auth_router)
api_v1_router.include_router(users_router)
api_v1_router.include_router(profile_router)
api_v1_router.include_router(categories_router)
api_v1_router.include_router(health_tips_router)
api_v1_router.include_router(notifications_router)

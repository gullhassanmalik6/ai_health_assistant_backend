"""AI Doctor API application factory."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.openapi.utils import get_openapi
from slowapi.middleware import SlowAPIMiddleware

from app.api.health import router as health_router
from app.api.v1.router import api_v1_router
from app.core.config import settings
from app.core.database import dispose_engine, init_engine
from app.core.error_handlers import register_exception_handlers
from app.core.firebase import close_http_client, init_firebase
from app.core.logging import setup_logging
from app.core.middleware import RequestContextMiddleware
from app.core.rate_limit import limiter

OPENAPI_TAGS = [
    {
        "name": "Authentication",
        "description": "Firebase-backed registration, login, social, guest, and session endpoints.",
    },
    {"name": "Users", "description": "Current-user profile identity and account deletion."},
    {"name": "Profile", "description": "Health profile and completion scoring."},
    {"name": "Allergies", "description": "Structured allergy records owned by the authenticated user."},
    {"name": "Conditions", "description": "Structured existing-disease records."},
    {"name": "Medications", "description": "Current medication profile (not prescription analysis)."},
    {"name": "Health", "description": "Liveness and readiness probes."},
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    init_engine()
    if settings.is_test:
        from app.core.database import get_engine
        from app.models import Base

        async with get_engine().begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
    init_firebase()
    yield
    await close_http_client()
    await dispose_engine()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "Phase 1 backend for AI Doctor. Flutter and web clients authenticate with "
            "Firebase and call this API over HTTPS. Passwords, AI keys, and database "
            "credentials never belong on the client."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
        swagger_ui_parameters={"persistAuthorization": True},
    )
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )
    if settings.allowed_hosts_list and "*" not in settings.allowed_hosts_list:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts_list)

    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(api_v1_router, prefix="/api/v1")

    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
            tags=OPENAPI_TAGS,
        )
        schema.setdefault("components", {}).setdefault("securitySchemes", {})["BearerAuth"] = {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Firebase ID token. Send as: Authorization: Bearer <idToken>",
        }
        schema["security"] = [{"BearerAuth": []}]
        app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = custom_openapi
    return app


app = create_app()

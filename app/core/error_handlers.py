"""Centralized exception handlers. Clients never receive stack traces."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.constants import ErrorCode
from app.core.exceptions import AppError
from app.core.logging import get_logger
from app.utils.response import error_payload

logger = get_logger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        logger.info(
            "application_error code=%s status=%s",
            exc.error_code,
            exc.status_code,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=error_payload(exc.message, exc.error_code, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        safe_details = []
        for error in exc.errors():
            safe_details.append(
                {
                    "loc": error.get("loc"),
                    "msg": error.get("msg"),
                    "type": error.get("type"),
                }
            )
        logger.info(
            "validation_error",
        )
        return JSONResponse(
            status_code=422,
            content=error_payload(
                "Request validation failed.",
                ErrorCode.VALIDATION_ERROR,
                safe_details,
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        if exc.status_code == 401:
            code = ErrorCode.AUTH_TOKEN_INVALID
            message = exc.detail if isinstance(exc.detail, str) else "Invalid authentication token."
        elif exc.status_code == 403:
            code = ErrorCode.FORBIDDEN
            message = exc.detail if isinstance(exc.detail, str) else "Forbidden."
        elif exc.status_code == 404:
            code = ErrorCode.NOT_FOUND
            message = exc.detail if isinstance(exc.detail, str) else "Resource not found."
        elif exc.status_code == 429:
            code = ErrorCode.RATE_LIMITED
            message = "Too many requests. Please try again later."
        else:
            code = ErrorCode.INTERNAL_ERROR if exc.status_code >= 500 else ErrorCode.VALIDATION_ERROR
            message = exc.detail if isinstance(exc.detail, str) else "Request failed."
        return JSONResponse(
            status_code=exc.status_code,
            content=error_payload(message, code),
        )

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content=error_payload(
                "Too many requests. Please try again later.",
                ErrorCode.RATE_LIMITED,
            ),
        )

    @app.exception_handler(IntegrityError)
    async def integrity_handler(request: Request, exc: IntegrityError) -> JSONResponse:
        logger.warning(
            "database_integrity_error",
        )
        return JSONResponse(
            status_code=409,
            content=error_payload("Resource conflict.", ErrorCode.CONFLICT),
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.error(
            "database_error category=%s",
            type(exc).__name__,
        )
        return JSONResponse(
            status_code=500,
            content=error_payload(
                "A database error occurred.",
                ErrorCode.DATABASE_ERROR,
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "unhandled_error category=%s",
            type(exc).__name__,
        )
        return JSONResponse(
            status_code=500,
            content=error_payload(
                "An unexpected error occurred.",
                ErrorCode.INTERNAL_ERROR,
            ),
        )

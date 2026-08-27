"""Domain exceptions mapped to consistent API error responses."""

from typing import Any

from app.core.constants import ErrorCode


class AppError(Exception):
    """Base application error. Never leak internals to clients."""

    def __init__(
        self,
        message: str,
        *,
        error_code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        status_code: int = 500,
        details: Any = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details


class AuthenticationError(AppError):
    def __init__(
        self,
        message: str = "Invalid authentication token.",
        *,
        error_code: ErrorCode = ErrorCode.AUTH_TOKEN_INVALID,
        details: Any = None,
    ) -> None:
        super().__init__(
            message,
            error_code=error_code,
            status_code=401,
            details=details,
        )


class AuthorizationError(AppError):
    def __init__(
        self,
        message: str = "You are not allowed to perform this action.",
        *,
        error_code: ErrorCode = ErrorCode.FORBIDDEN,
        details: Any = None,
    ) -> None:
        super().__init__(
            message,
            error_code=error_code,
            status_code=403,
            details=details,
        )


class NotFoundError(AppError):
    def __init__(
        self,
        message: str = "Resource not found.",
        *,
        error_code: ErrorCode = ErrorCode.NOT_FOUND,
        details: Any = None,
    ) -> None:
        super().__init__(
            message,
            error_code=error_code,
            status_code=404,
            details=details,
        )


class ConflictError(AppError):
    def __init__(
        self,
        message: str = "Resource already exists.",
        *,
        error_code: ErrorCode = ErrorCode.CONFLICT,
        details: Any = None,
    ) -> None:
        super().__init__(
            message,
            error_code=error_code,
            status_code=409,
            details=details,
        )


class ValidationAppError(AppError):
    def __init__(
        self,
        message: str = "Request validation failed.",
        *,
        details: Any = None,
    ) -> None:
        super().__init__(
            message,
            error_code=ErrorCode.VALIDATION_ERROR,
            status_code=422,
            details=details,
        )


class RateLimitError(AppError):
    def __init__(self, message: str = "Too many requests. Please try again later.") -> None:
        super().__init__(
            message,
            error_code=ErrorCode.RATE_LIMITED,
            status_code=429,
        )


class FirebaseServiceError(AppError):
    def __init__(
        self,
        message: str = "Identity service is temporarily unavailable.",
        *,
        details: Any = None,
        status_code: int = 502,
    ) -> None:
        super().__init__(
            message,
            error_code=ErrorCode.FIREBASE_ERROR,
            status_code=status_code,
            details=details,
        )

"""Consistent API envelope helpers."""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str
    data: T | None = None


class APIErrorResponse(BaseModel):
    success: bool = False
    message: str
    error_code: str
    details: Any = None


def success_payload(message: str, data: Any = None) -> dict[str, Any]:
    return {"success": True, "message": message, "data": data}


def error_payload(message: str, error_code: str, details: Any = None) -> dict[str, Any]:
    return {
        "success": False,
        "message": message,
        "error_code": error_code,
        "details": details,
    }

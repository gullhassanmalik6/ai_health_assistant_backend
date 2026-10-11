"""Turn validation failures into {field: message} maps for Flutter forms."""

from __future__ import annotations

from typing import Any

from app.core.constants import HEIGHT_BOUNDS, WEIGHT_BOUNDS, HeightUnit, WeightUnit


def strip_period(message: str) -> str:
    return message.rstrip(" .")


def field_path_from_loc(loc: tuple[Any, ...] | list[Any]) -> str:
    parts: list[str] = []
    for item in loc:
        if item in {"body", "query", "path", "header"}:
            continue
        if isinstance(item, int):
            if parts:
                parts[-1] = f"{parts[-1]}.{item}"
            else:
                parts.append(str(item))
            continue
        parts.append(str(item))
    return ".".join(parts) or "request"


def _capitalize(message: str) -> str:
    cleaned = strip_period(message)
    if not cleaned:
        return "This value is not valid"
    return cleaned[0].upper() + cleaned[1:]


def humanize_validation_message(field: str, msg: str, error_type: str = "") -> str:
    raw = (msg or "").strip()
    for prefix in ("Value error, ", "Value error:", "Assertion failed, "):
        if raw.startswith(prefix):
            raw = raw[len(prefix) :].strip()
    lower = raw.lower()
    type_lower = (error_type or "").lower()
    leaf = field.split(".")[-1]

    if leaf == "email" or field.endswith(".email"):
        if "email" in lower or "value_error" in type_lower:
            return "Enter a valid email address"

    if leaf in {"password", "new_password", "current_password"}:
        if "at least" in lower or "too_short" in type_lower or "min_length" in type_lower:
            return "Password must be 8 to 128 characters"
        if "at most" in lower or "too_long" in type_lower:
            return "Password must be 8 to 128 characters"

    if leaf == "name" and ("empty" in lower or "required" in lower or "at least" in lower):
        return "Enter your full name"

    if "missing" in type_lower or lower.startswith("field required"):
        if leaf == "name":
            return "Enter your full name"
        return "This field is required"

    if leaf == "blood_group" or field.endswith("blood_group"):
        return "Choose a valid blood group"

    if leaf == "gender" or field.endswith("gender"):
        return "Choose female, male or other"

    if field.startswith("height") or leaf == "height":
        if "greater than" in lower or "positive" in lower:
            return "Height must be a positive number"
        if HeightUnit.CM.value in field or "cm" in lower:
            low, high = HEIGHT_BOUNDS[HeightUnit.CM]
            return f"Height must be between {int(low)} and {int(high)} cm"
        return strip_period(raw) or "Height is not valid"

    if field.startswith("weight") or leaf == "weight":
        if "greater than" in lower or "positive" in lower:
            return "Weight must be a positive number"
        if WeightUnit.KG.value in field or "kg" in lower:
            low, high = WEIGHT_BOUNDS[WeightUnit.KG]
            return f"Weight must be between {int(low)} and {int(high)} kg"
        return strip_period(raw) or "Weight is not valid"

    if "enum" in type_lower or "literal" in type_lower:
        return f"{_capitalize(leaf.replace('_', ' '))} is not valid"

    return _capitalize(raw)


def details_from_pydantic_errors(errors: list[dict[str, Any]]) -> dict[str, str]:
    details: dict[str, str] = {}
    for error in errors:
        field = field_path_from_loc(error.get("loc") or ())
        if field in details:
            continue
        details[field] = humanize_validation_message(
            field,
            str(error.get("msg") or ""),
            str(error.get("type") or ""),
        )
    return details

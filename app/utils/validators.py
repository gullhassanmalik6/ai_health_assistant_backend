"""Input validation helpers. Health values are checked for physical plausibility."""

from datetime import date, timedelta

import phonenumbers
from phonenumbers import NumberParseException

from app.core.constants import (
    HEIGHT_BOUNDS,
    MAX_AGE_YEARS,
    MAX_PASSWORD_LENGTH,
    MIN_PASSWORD_LENGTH,
    PASSWORD_REQUIRE_NUMBER,
    WEIGHT_BOUNDS,
    HeightUnit,
    WeightUnit,
)
from app.core.exceptions import ValidationAppError
from app.utils.validation_errors import strip_period


def _field_error(field: str, message: str) -> ValidationAppError:
    clean = strip_period(message)
    return ValidationAppError(
        "Please check the highlighted fields.",
        details={field: clean},
    )


def validate_password(password: str, *, field: str = "password") -> str:
    """Shared password rule for Sign Up and Change Password."""
    value = password or ""
    if len(value) < MIN_PASSWORD_LENGTH or len(value) > MAX_PASSWORD_LENGTH:
        raise _field_error(field, "Password must be 8 to 128 characters")
    if PASSWORD_REQUIRE_NUMBER and not any(char.isdigit() for char in value):
        raise _field_error(field, "Password must contain a number")
    return value


def validate_date_of_birth(
    value: date,
    *,
    max_age: int = MAX_AGE_YEARS,
    field: str = "date_of_birth",
) -> date:
    today = date.today()
    if value > today:
        raise _field_error(field, "Date of birth cannot be in the future")
    oldest = today - timedelta(days=max_age * 365 + max_age // 4)
    if value < oldest:
        raise _field_error(field, "Date of birth is not plausible")
    return value


def validate_height(value: float, unit: HeightUnit, *, field: str = "height") -> float:
    if value <= 0:
        raise _field_error(field, "Height must be a positive number")
    low, high = HEIGHT_BOUNDS[unit]
    if value < low or value > high:
        if unit == HeightUnit.CM:
            message = f"Height must be between {int(low)} and {int(high)} cm"
        else:
            message = f"Height must be between {low} and {high} {unit}"
        raise _field_error(field, message)
    return value


def validate_weight(value: float, unit: WeightUnit, *, field: str = "weight") -> float:
    if value <= 0:
        raise _field_error(field, "Weight must be a positive number")
    low, high = WEIGHT_BOUNDS[unit]
    if value < low or value > high:
        if unit == WeightUnit.KG:
            message = f"Weight must be between {int(low)} and {int(high)} kg"
        else:
            message = f"Weight must be between {low} and {high} {unit}"
        raise _field_error(field, message)
    return value


def height_to_cm(value: float, unit: HeightUnit) -> float:
    if unit == HeightUnit.CM:
        return round(value, 2)
    if unit == HeightUnit.FT:
        return round(value * 30.48, 2)
    return round(value * 2.54, 2)


def weight_to_kg(value: float, unit: WeightUnit) -> float:
    if unit == WeightUnit.KG:
        return round(value, 2)
    return round(value * 0.45359237, 2)


def validate_phone_number(value: str, *, field: str = "emergency_contact_phone") -> str:
    """Require international format. No default country is assumed."""
    raw = value.strip()
    if not raw.startswith("+"):
        raise _field_error(
            field,
            "Phone number must be in international format, starting with '+' and a country code",
        )
    try:
        parsed = phonenumbers.parse(raw, None)
    except NumberParseException as exc:
        raise _field_error(field, "Phone number is not valid") from exc
    if not phonenumbers.is_valid_number(parsed):
        raise _field_error(field, "Phone number is not valid")
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)

"""Input validation helpers. Health values are checked for physical plausibility."""

from datetime import date, timedelta

import phonenumbers
from phonenumbers import NumberParseException

from app.core.constants import (
    HEIGHT_BOUNDS,
    MAX_AGE_YEARS,
    WEIGHT_BOUNDS,
    HeightUnit,
    WeightUnit,
)
from app.core.exceptions import ValidationAppError


def validate_date_of_birth(value: date) -> date:
    today = date.today()
    if value > today:
        raise ValidationAppError("Date of birth cannot be in the future.")
    oldest = today - timedelta(days=MAX_AGE_YEARS * 365 + MAX_AGE_YEARS // 4)
    if value < oldest:
        raise ValidationAppError("Date of birth is not plausible.")
    return value


def validate_height(value: float, unit: HeightUnit) -> float:
    if value <= 0:
        raise ValidationAppError("Height must be a positive number.")
    low, high = HEIGHT_BOUNDS[unit]
    if value < low or value > high:
        raise ValidationAppError(f"Height must be between {low} and {high} {unit}.")
    return value


def validate_weight(value: float, unit: WeightUnit) -> float:
    if value <= 0:
        raise ValidationAppError("Weight must be a positive number.")
    low, high = WEIGHT_BOUNDS[unit]
    if value < low or value > high:
        raise ValidationAppError(f"Weight must be between {low} and {high} {unit}.")
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


def validate_phone_number(value: str) -> str:
    """Require international format. No default country is assumed."""
    raw = value.strip()
    if not raw.startswith("+"):
        raise ValidationAppError(
            "Phone number must be in international format, starting with '+' and a country code."
        )
    try:
        parsed = phonenumbers.parse(raw, None)
    except NumberParseException as exc:
        raise ValidationAppError("Phone number is not valid.") from exc
    if not phonenumbers.is_valid_number(parsed):
        raise ValidationAppError("Phone number is not valid.")
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)

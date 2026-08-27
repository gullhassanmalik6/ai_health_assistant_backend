"""Validator unit tests."""

from datetime import date, timedelta

import pytest

from app.core.constants import HeightUnit, WeightUnit
from app.core.exceptions import ValidationAppError
from app.utils.validators import (
    height_to_cm,
    validate_date_of_birth,
    validate_height,
    validate_phone_number,
    validate_weight,
    weight_to_kg,
)


def test_reject_future_dob():
    with pytest.raises(ValidationAppError):
        validate_date_of_birth(date.today() + timedelta(days=1))


def test_accept_reasonable_dob():
    assert validate_date_of_birth(date(1990, 5, 1)) == date(1990, 5, 1)


def test_height_and_weight_bounds():
    validate_height(170, HeightUnit.CM)
    validate_weight(70, WeightUnit.KG)
    with pytest.raises(ValidationAppError):
        validate_height(10, HeightUnit.CM)
    with pytest.raises(ValidationAppError):
        validate_weight(-1, WeightUnit.KG)


def test_canonical_units():
    assert height_to_cm(1, HeightUnit.IN) == 2.54
    assert weight_to_kg(10, WeightUnit.LB) == round(10 * 0.45359237, 2)


def test_phone_requires_international_format():
    with pytest.raises(ValidationAppError):
        validate_phone_number("03001234567")
    with pytest.raises(ValidationAppError):
        validate_phone_number("14155552671")
    assert validate_phone_number("+14155552671").startswith("+")

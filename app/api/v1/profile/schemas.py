"""Profile, allergy, condition, and medication schemas."""

from datetime import date, datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.constants import (
    MAX_ALLERGY_NAME_LENGTH,
    MAX_CONDITION_NAME_LENGTH,
    MAX_MEDICATION_NAME_LENGTH,
    MAX_NAME_LENGTH,
    MAX_NOTES_LENGTH,
    AllergySeverity,
    BloodGroup,
    ConditionStatus,
    Gender,
    HeightUnit,
    MedicationRoute,
    WeightUnit,
)
from app.utils.validators import validate_date_of_birth, validate_height, validate_phone_number, validate_weight


class Measurement(BaseModel):
    value: float = Field(gt=0)
    unit: str


class HeightMeasurement(Measurement):
    unit: HeightUnit

    @model_validator(mode="after")
    def check_bounds(self) -> Self:
        validate_height(self.value, self.unit)
        return self


class WeightMeasurement(Measurement):
    unit: WeightUnit

    @model_validator(mode="after")
    def check_bounds(self) -> Self:
        validate_weight(self.value, self.unit)
        return self


class AllergyData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    allergy_name: str
    reaction: str | None = None
    severity: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class ConditionData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    condition_name: str
    diagnosed_date: date | None = None
    status: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class MedicationData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    medication_name: str
    dosage: str | None = None
    frequency: str | None = None
    route: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class ProfileData(BaseModel):
    id: str
    user_id: str
    name: str | None = None
    email: str | None = None
    gender: str | None = None
    date_of_birth: date | None = None
    height: HeightMeasurement | None = None
    weight: WeightMeasurement | None = None
    blood_group: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    profile_photo_url: str | None = None
    onboarding_completed: bool = False
    profile_completed: bool = False
    profile_completion_percentage: int = 0
    allergies: list[AllergyData] = Field(default_factory=list)
    conditions: list[ConditionData] = Field(default_factory=list)
    medications: list[MedicationData] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ProfileWriteRequest(BaseModel):
    name: str | None = Field(default=None, max_length=MAX_NAME_LENGTH)
    gender: Gender | None = None
    date_of_birth: date | None = None
    height: HeightMeasurement | None = None
    weight: WeightMeasurement | None = None
    blood_group: BloodGroup | None = None
    emergency_contact_name: str | None = Field(default=None, max_length=MAX_NAME_LENGTH)
    emergency_contact_phone: str | None = None
    profile_photo_url: str | None = Field(default=None, max_length=1024)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("date_of_birth")
    @classmethod
    def check_dob(cls, value: date | None) -> date | None:
        if value is None:
            return None
        return validate_date_of_birth(value)

    @field_validator("emergency_contact_phone")
    @classmethod
    def check_phone(cls, value: str | None) -> str | None:
        if value is None or value.strip() == "":
            return None
        return validate_phone_number(value)


class ProfilePutRequest(ProfileWriteRequest):
    """Full replace of editable profile fields. Omitted optional fields are cleared."""


class ProfilePatchRequest(ProfileWriteRequest):
    """Partial update. Omitted fields are left unchanged."""


class AllergyWriteRequest(BaseModel):
    allergy_name: str = Field(min_length=1, max_length=MAX_ALLERGY_NAME_LENGTH)
    reaction: str | None = Field(default=None, max_length=255)
    severity: AllergySeverity | None = AllergySeverity.UNKNOWN
    notes: str | None = Field(default=None, max_length=MAX_NOTES_LENGTH)

    @field_validator("allergy_name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Allergy name cannot be empty.")
        return cleaned


class AllergyPatchRequest(BaseModel):
    allergy_name: str | None = Field(default=None, min_length=1, max_length=MAX_ALLERGY_NAME_LENGTH)
    reaction: str | None = Field(default=None, max_length=255)
    severity: AllergySeverity | None = None
    notes: str | None = Field(default=None, max_length=MAX_NOTES_LENGTH)


class ConditionWriteRequest(BaseModel):
    condition_name: str = Field(min_length=1, max_length=MAX_CONDITION_NAME_LENGTH)
    diagnosed_date: date | None = None
    status: ConditionStatus | None = ConditionStatus.ACTIVE
    notes: str | None = Field(default=None, max_length=MAX_NOTES_LENGTH)

    @field_validator("condition_name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Condition name cannot be empty.")
        return cleaned

    @field_validator("diagnosed_date")
    @classmethod
    def check_diagnosed(cls, value: date | None) -> date | None:
        if value and value > date.today():
            raise ValueError("Diagnosed date cannot be in the future.")
        return value


class ConditionPatchRequest(BaseModel):
    condition_name: str | None = Field(default=None, min_length=1, max_length=MAX_CONDITION_NAME_LENGTH)
    diagnosed_date: date | None = None
    status: ConditionStatus | None = None
    notes: str | None = Field(default=None, max_length=MAX_NOTES_LENGTH)


class MedicationWriteRequest(BaseModel):
    medication_name: str = Field(min_length=1, max_length=MAX_MEDICATION_NAME_LENGTH)
    dosage: str | None = Field(default=None, max_length=100)
    frequency: str | None = Field(default=None, max_length=100)
    route: MedicationRoute | None = None
    notes: str | None = Field(default=None, max_length=MAX_NOTES_LENGTH)

    @field_validator("medication_name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Medication name cannot be empty.")
        return cleaned


class MedicationPatchRequest(BaseModel):
    medication_name: str | None = Field(default=None, min_length=1, max_length=MAX_MEDICATION_NAME_LENGTH)
    dosage: str | None = Field(default=None, max_length=100)
    frequency: str | None = Field(default=None, max_length=100)
    route: MedicationRoute | None = None
    notes: str | None = Field(default=None, max_length=MAX_NOTES_LENGTH)


class ProfileCompletionData(BaseModel):
    percentage: int
    is_complete: bool
    completed: list[str]
    missing: list[str]

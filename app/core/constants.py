"""Shared enumerations, limits, and error codes."""

from enum import StrEnum


class Environment(StrEnum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


class AuthProvider(StrEnum):
    EMAIL = "email"
    GOOGLE = "google"
    APPLE = "apple"
    ANONYMOUS = "anonymous"


class Gender(StrEnum):
    FEMALE = "female"
    MALE = "male"
    OTHER = "other"


class BloodGroup(StrEnum):
    A_POSITIVE = "A+"
    A_NEGATIVE = "A-"
    B_POSITIVE = "B+"
    B_NEGATIVE = "B-"
    AB_POSITIVE = "AB+"
    AB_NEGATIVE = "AB-"
    O_POSITIVE = "O+"
    O_NEGATIVE = "O-"


class HeightUnit(StrEnum):
    CM = "cm"
    FT = "ft"
    IN = "in"


class WeightUnit(StrEnum):
    KG = "kg"
    LB = "lb"


class AllergySeverity(StrEnum):
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"
    UNKNOWN = "unknown"


class ConditionStatus(StrEnum):
    ACTIVE = "active"
    MANAGED = "managed"
    RESOLVED = "resolved"
    IN_REMISSION = "in_remission"


class MedicationRoute(StrEnum):
    ORAL = "oral"
    TOPICAL = "topical"
    INHALED = "inhaled"
    INJECTION = "injection"
    OTHER = "other"


class ErrorCode(StrEnum):
    AUTH_TOKEN_MISSING = "AUTH_TOKEN_MISSING"
    AUTH_TOKEN_INVALID = "AUTH_TOKEN_INVALID"
    AUTH_TOKEN_EXPIRED = "AUTH_TOKEN_EXPIRED"
    AUTH_SESSION_REVOKED = "AUTH_SESSION_REVOKED"
    AUTH_USER_NOT_FOUND = "AUTH_USER_NOT_FOUND"
    AUTH_ACCOUNT_DISABLED = "AUTH_ACCOUNT_DISABLED"
    AUTH_GUEST_FORBIDDEN = "AUTH_GUEST_FORBIDDEN"
    AUTH_INVALID_CREDENTIALS = "AUTH_INVALID_CREDENTIALS"
    AUTH_ACCOUNT_EXISTS = "AUTH_ACCOUNT_EXISTS"
    AUTH_EMAIL_NOT_VERIFIED = "AUTH_EMAIL_NOT_VERIFIED"
    AUTH_PROVIDER_MISMATCH = "AUTH_PROVIDER_MISMATCH"
    AUTH_WEAK_PASSWORD = "AUTH_WEAK_PASSWORD"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    RATE_LIMITED = "RATE_LIMITED"
    FIREBASE_ERROR = "FIREBASE_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


FIREBASE_PROVIDER_MAP = {
    "password": AuthProvider.EMAIL,
    "google.com": AuthProvider.GOOGLE,
    "apple.com": AuthProvider.APPLE,
    "anonymous": AuthProvider.ANONYMOUS,
}

# Fields that contribute to backend-calculated profile completion.
PROFILE_COMPLETION_FIELDS = (
    "name",
    "gender",
    "date_of_birth",
    "height",
    "weight",
    "blood_group",
    "emergency_contact",
)

# Physiological sanity bounds used by validators.
HEIGHT_BOUNDS = {
    HeightUnit.CM: (50.0, 250.0),
    HeightUnit.FT: (1.5, 8.5),
    HeightUnit.IN: (20.0, 100.0),
}
WEIGHT_BOUNDS = {
    WeightUnit.KG: (2.0, 400.0),
    WeightUnit.LB: (4.0, 880.0),
}

MAX_AGE_YEARS = 130
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128
MAX_NAME_LENGTH = 150
MAX_NOTES_LENGTH = 2000
MAX_MEDICATION_NAME_LENGTH = 200
MAX_ALLERGY_NAME_LENGTH = 200
MAX_CONDITION_NAME_LENGTH = 200

GENERIC_PASSWORD_RESET_MESSAGE = (
    "If the account exists, password reset instructions have been sent."
)

# Firebase REST endpoints (Identity Toolkit).
FIREBASE_SIGN_UP_URL = "https://identitytoolkit.googleapis.com/v1/accounts:signUp"
FIREBASE_SIGN_IN_URL = (
    "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
)
FIREBASE_OOB_URL = "https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode"
FIREBASE_RESET_PASSWORD_URL = (
    "https://identitytoolkit.googleapis.com/v1/accounts:resetPassword"
)
FIREBASE_ACCOUNT_LOOKUP_URL = (
    "https://identitytoolkit.googleapis.com/v1/accounts:lookup"
)
FIREBASE_TOKEN_URL = "https://securetoken.googleapis.com/v1/token"

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
    UNKNOWN = "unknown"


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


class TintKey(StrEnum):
    BLUE = "blue"
    CORAL = "coral"
    AMBER = "amber"
    PURPLE = "purple"
    GREEN = "green"
    TEAL = "teal"
    PINK = "pink"


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
    AUTH_PASSWORD_NOT_SUPPORTED = "AUTH_PASSWORD_NOT_SUPPORTED"
    AUTH_INVALID_CURRENT_PASSWORD = "AUTH_INVALID_CURRENT_PASSWORD"
    AUTH_PASSWORD_UNCHANGED = "AUTH_PASSWORD_UNCHANGED"
    AUTH_CODE_INVALID = "AUTH_CODE_INVALID"
    AUTH_CODE_EXPIRED = "AUTH_CODE_EXPIRED"
    AUTH_CODE_ATTEMPTS_EXCEEDED = "AUTH_CODE_ATTEMPTS_EXCEEDED"
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
# Emergency contact is stored but not counted — no screen collects it.
PROFILE_COMPLETION_FIELDS = (
    "name",
    "date_of_birth",
    "gender",
    "height",
    "weight",
    "blood_group",
)

# Pending product decisions — flip these in one place when the app owner decides.
PROFILE_COMPLETION_COUNT_PHOTO = False
PROFILE_COMPLETION_COUNT_ALLERGIES = False
PROFILE_COMPLETION_COUNT_CONDITIONS = False
BLOOD_GROUP_UNKNOWN_COUNTS_AS_FILLED = True

# Pending: Change Password screen checks for a number; Sign Up currently does not.
# Keep both on the same rule. Flip this when product decides.
PASSWORD_REQUIRE_NUMBER = False

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
MAX_AGE_YEARS_PERSONAL = 120
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128
MAX_NAME_LENGTH = 150
PERSONAL_NAME_MAX_LENGTH = 100
MAX_NOTES_LENGTH = 2000
MAX_MEDICATION_NAME_LENGTH = 200
MAX_ALLERGY_NAME_LENGTH = 200
MAX_CONDITION_NAME_LENGTH = 200
HEALTH_LIST_NAME_MAX_LENGTH = 100
HEALTH_LIST_MAX_ITEMS = 50

PHOTO_MAX_BYTES = 5 * 1024 * 1024
PHOTO_ALLOWED_CONTENT_TYPES = ("image/jpeg", "image/jpg", "image/png", "image/webp")
PHOTO_SIGNED_URL_TTL_SECONDS = 3600

VERIFICATION_CODE_LENGTH = 6
VERIFICATION_CODE_TTL_SECONDS = 10 * 60
VERIFICATION_RESEND_COOLDOWN_SECONDS = 60
VERIFICATION_MAX_ATTEMPTS = 5
VERIFICATION_EMAIL_SUBJECT = "Your AI Doctor verification code"

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

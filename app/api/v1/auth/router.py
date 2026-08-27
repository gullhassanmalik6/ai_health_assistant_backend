"""Authentication endpoints. Business logic lives in AuthService."""

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    ResetPasswordRequest,
    SocialAuthRequest,
    VerificationStatusData,
)
from app.api.v1.serializers import auth_data, compute_completion
from app.core.constants import AuthProvider
from app.core.rate_limit import auth_limit, limiter
from app.dependencies.auth import AuthenticatedContext, get_current_context, get_current_user
from app.dependencies.database import get_db
from app.models.user import User
from app.services.auth_service import AuthService
from app.utils.response import success_payload

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _auth_response(result, message: str, status_code: int = 200):
    completion = compute_completion(result.user)
    payload = auth_data(result.user, result.session, completion)
    return success_payload(message, payload.model_dump(mode="json")), status_code


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    summary="Register with email and password",
    description=(
        "Creates a Firebase identity (password is never stored in PostgreSQL), "
        "then creates the application user and an empty health profile."
    ),
)
@limiter.limit(auth_limit())
async def register(
    request: Request,
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await AuthService(db).register(
        email=body.email,
        password=body.password,
        name=body.name,
    )
    data, code = _auth_response(result, "Account created successfully.", 201)
    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=code, content=data)


@router.post(
    "/login",
    summary="Sign in with email and password",
    description="Authenticates against Firebase and returns application user state.",
)
@limiter.limit(auth_limit())
async def login(
    request: Request,
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await AuthService(db).login(email=body.email, password=body.password)
    data, _ = _auth_response(result, "Login successful.")
    return data


@router.post(
    "/google",
    summary="Sign in with Google",
    description="Accepts a Firebase ID token obtained after Google sign-in on the client. Identity is taken only from the verified token.",
)
@limiter.limit(auth_limit())
async def google_auth(
    request: Request,
    body: SocialAuthRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await AuthService(db).authenticate_with_id_token(
        body.id_token,
        expected_provider=AuthProvider.GOOGLE,
    )
    data, _ = _auth_response(result, "Google authentication successful.")
    return data


@router.post(
    "/apple",
    summary="Sign in with Apple",
    description="Accepts a Firebase ID token obtained after Apple sign-in on the client. Identity is taken only from the verified token.",
)
@limiter.limit(auth_limit())
async def apple_auth(
    request: Request,
    body: SocialAuthRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await AuthService(db).authenticate_with_id_token(
        body.id_token,
        expected_provider=AuthProvider.APPLE,
    )
    data, _ = _auth_response(result, "Apple authentication successful.")
    return data


@router.post(
    "/guest",
    status_code=status.HTTP_201_CREATED,
    summary="Start a guest session",
    description="Creates an anonymous Firebase identity and a guest application user that can later be upgraded.",
)
@limiter.limit(auth_limit())
async def guest_auth(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    result = await AuthService(db).start_guest_session()
    data, code = _auth_response(result, "Guest session created.", 201)
    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=code, content=data)


@router.post(
    "/logout",
    summary="Log out",
    description="Invalidates application-level sessions issued before this moment. Future revocation can use the same contract.",
)
async def logout(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await AuthService(db).logout(user)
    return success_payload("Logged out successfully.", None)


@router.post(
    "/forgot-password",
    summary="Request a password reset email",
    description="Always returns a generic message so account existence is not leaked.",
)
@limiter.limit(auth_limit())
async def forgot_password(
    request: Request,
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    message = await AuthService(db).forgot_password(body.email)
    return success_payload(message, None)


@router.post(
    "/reset-password",
    summary="Confirm a password reset",
    description="Completes a Firebase password reset using the action code from the email link.",
)
@limiter.limit(auth_limit())
async def reset_password(
    request: Request,
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    await AuthService(db).reset_password(oob_code=body.oob_code, new_password=body.new_password)
    return success_payload("Password has been reset successfully.", None)


@router.post(
    "/send-verification",
    summary="Send email verification",
    description="Sends a Firebase email verification message to the current user.",
)
async def send_verification(
    context: AuthenticatedContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    await AuthService(db).send_verification(context.raw_token)
    return success_payload("Verification email sent if a mailbox is associated with this account.", None)


@router.get(
    "/verification-status",
    summary="Email verification status",
    description="Derived from the verified Firebase identity, then synced to the application user.",
)
async def verification_status(
    context: AuthenticatedContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    verified = await AuthService(db).verification_status(context.user, context.claims)
    return success_payload(
        "Verification status retrieved.",
        VerificationStatusData(verified=verified).model_dump(),
    )


@router.get(
    "/session",
    summary="Initialize session (splash)",
    description="Returns the current application user and profile completion for splash/session bootstrap.",
)
async def session_status(
    user: User = Depends(get_current_user),
):
    completion = compute_completion(user)
    payload = auth_data(user, None, completion)
    return success_payload("Session retrieved.", payload.model_dump(mode="json"))


@router.post(
    "/refresh",
    summary="Refresh Firebase ID token",
)
@limiter.limit(auth_limit())
async def refresh_token(
    request: Request,
    body: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await AuthService(db).refresh(body.refresh_token)
    data, _ = _auth_response(result, "Token refreshed.")
    return data

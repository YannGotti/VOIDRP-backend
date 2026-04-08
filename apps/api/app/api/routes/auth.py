from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from apps.api.app.db import get_db_session
from apps.api.app.schemas.auth import (
    EmailActionResponse,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    RefreshRequest,
    RefreshResponse,
    RegisterRequest,
    RegisterResponse,
    RequestPasswordResetRequest,
    ResendVerificationRequest,
    ResetPasswordRequest,
    VerifyEmailRequest,
)
from apps.api.app.services.auth_service import (
    AuthService,
    AuthenticationError,
    ConflictError,
    TokenValidationError,
)
from apps.api.app.services.email_service import LoggingEmailService

router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> AuthService:
    return AuthService(session=session, email_service=LoggingEmailService())


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> RegisterResponse:
    try:
        user, player_account = auth_service.register_user(
            site_login=payload.site_login,
            minecraft_nickname=payload.minecraft_nickname,
            email=payload.email,
            password=payload.password,
        )
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return RegisterResponse(
        message="User registered successfully. Email verification has been requested.",
        user=user,
        player_account=player_account,
        verification_requested=True,
    )


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> LoginResponse:
    try:
        result = auth_service.login(
            login=payload.login,
            password=payload.password,
            device_name=payload.device_name,
        )
    except AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    return LoginResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        access_expires_in=result.access_expires_in,
        refresh_expires_in=result.refresh_expires_in,
        user=result.user,
        player_account=result.player_account,
    )


@router.post("/refresh", response_model=RefreshResponse)
def refresh(
    payload: RefreshRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> RefreshResponse:
    try:
        result = auth_service.refresh(
            raw_refresh_token=payload.refresh_token,
            device_name=payload.device_name,
        )
    except AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    return RefreshResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        access_expires_in=result.access_expires_in,
        refresh_expires_in=result.refresh_expires_in,
        user=result.user,
        player_account=result.player_account,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    payload: LogoutRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> None:
    auth_service.logout(raw_refresh_token=payload.refresh_token)


@router.post("/verify-email", response_model=EmailActionResponse)
def verify_email(
    payload: VerifyEmailRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> EmailActionResponse:
    try:
        auth_service.verify_email(raw_token=payload.token)
    except TokenValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return EmailActionResponse(message="Email successfully verified.")


@router.post("/resend-verification", response_model=EmailActionResponse)
def resend_verification(
    payload: ResendVerificationRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> EmailActionResponse:
    auth_service.resend_verification_email(email=payload.email)
    return EmailActionResponse(
        message="If the account exists and email is not verified, a new verification token has been issued."
    )


@router.post("/request-password-reset", response_model=EmailActionResponse)
def request_password_reset(
    payload: RequestPasswordResetRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> EmailActionResponse:
    auth_service.request_password_reset(email=payload.email)
    return EmailActionResponse(
        message="If the account exists, a password reset token has been issued."
    )


@router.post("/reset-password", response_model=EmailActionResponse)
def reset_password(
    payload: ResetPasswordRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> EmailActionResponse:
    try:
        auth_service.reset_password(raw_token=payload.token, new_password=payload.new_password)
    except TokenValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return EmailActionResponse(message="Password has been reset successfully.")

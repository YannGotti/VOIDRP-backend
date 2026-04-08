from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from apps.api.app.config import get_settings
from apps.api.app.core.security import (
    build_access_token,
    generate_opaque_token,
    hash_opaque_token,
    hash_password,
    utc_now,
    verify_password,
)
from apps.api.app.models.email_token import EmailToken, EmailTokenPurpose
from apps.api.app.models.player_account import PlayerAccount
from apps.api.app.models.refresh_session import RefreshSession
from apps.api.app.models.user import User
from apps.api.app.repositories.user_repository import UserRepository
from apps.api.app.services.email_service import EmailMessage, EmailService
from apps.api.app.utils.normalization import (
    normalize_email,
    normalize_minecraft_nickname,
    normalize_site_login,
)


class AuthError(Exception):
    pass


class ConflictError(AuthError):
    pass


class AuthenticationError(AuthError):
    pass


class TokenValidationError(AuthError):
    pass


@dataclass(slots=True)
class LoginResult:
    access_token: str
    access_expires_in: int
    refresh_token: str
    refresh_expires_in: int
    user: User
    player_account: PlayerAccount


class AuthService:
    def __init__(self, session: Session, email_service: EmailService) -> None:
        self.session = session
        self.email_service = email_service
        self.user_repository = UserRepository(session)
        self.settings = get_settings()

    def register_user(
        self,
        *,
        site_login: str,
        minecraft_nickname: str,
        email: str,
        password: str,
    ) -> tuple[User, PlayerAccount]:
        login_raw, login_normalized = normalize_site_login(site_login)
        nickname_raw, nickname_normalized = normalize_minecraft_nickname(minecraft_nickname)
        email_normalized = normalize_email(email)

        if self.user_repository.get_by_site_login_normalized(login_normalized):
            raise ConflictError("site_login is already taken")

        if self.user_repository.get_by_email_normalized(email_normalized):
            raise ConflictError("email is already registered")

        existing_player = self.session.execute(
            select(PlayerAccount).where(
                PlayerAccount.minecraft_nickname_normalized == nickname_normalized
            )
        ).scalar_one_or_none()
        if existing_player:
            raise ConflictError("minecraft_nickname is already linked to another account")

        user = User(
            site_login=login_raw,
            site_login_normalized=login_normalized,
            email=email.strip(),
            email_normalized=email_normalized,
            password_hash=hash_password(password),
            email_verified=False,
            is_active=True,
        )
        player_account = PlayerAccount(
            minecraft_nickname=nickname_raw,
            minecraft_nickname_normalized=nickname_normalized,
            nickname_locked=True,
            legacy_auth_enabled=False,
        )
        user.player_account = player_account

        self.user_repository.add(user)
        self.session.flush()
        self._issue_email_token(user=user, purpose=EmailTokenPurpose.VERIFY_EMAIL)
        self.session.commit()
        self.session.refresh(user)
        self.session.refresh(player_account)

        return user, player_account

    def login(self, *, login: str, password: str, device_name: str) -> LoginResult:
        normalized_login = normalize_email(login)
        user = self.session.execute(
            select(User)
            .options(joinedload(User.player_account))
            .where(
                (User.site_login_normalized == normalized_login)
                | (User.email_normalized == normalized_login)
            )
        ).unique().scalar_one_or_none()

        if user is None or not verify_password(password, user.password_hash):
            raise AuthenticationError("invalid credentials")

        if not user.is_active:
            raise AuthenticationError("account is disabled")

        return self._issue_session(user=user, device_name=device_name)

    def refresh(self, *, raw_refresh_token: str, device_name: str) -> LoginResult:
        refresh_session = self.session.execute(
            select(RefreshSession)
            .where(RefreshSession.token_hash == hash_opaque_token(raw_refresh_token))
        ).scalar_one_or_none()

        if refresh_session is None:
            raise AuthenticationError("refresh token is invalid")

        if refresh_session.revoked_at is not None:
            raise AuthenticationError("refresh token is revoked")

        if refresh_session.expires_at <= utc_now():
            raise AuthenticationError("refresh token is expired")

        user = self.session.execute(
            select(User).options(joinedload(User.player_account)).where(User.id == refresh_session.user_id)
        ).unique().scalar_one()

        refresh_session.revoked_at = utc_now()
        refresh_session.last_used_at = utc_now()
        self.session.flush()

        return self._issue_session(user=user, device_name=device_name)

    def logout(self, *, raw_refresh_token: str) -> None:
        refresh_session = self.session.execute(
            select(RefreshSession)
            .where(RefreshSession.token_hash == hash_opaque_token(raw_refresh_token))
        ).scalar_one_or_none()

        if refresh_session is None:
            return

        refresh_session.revoked_at = utc_now()
        refresh_session.last_used_at = utc_now()
        self.session.commit()

    def verify_email(self, *, raw_token: str) -> User:
        email_token = self._get_valid_email_token(
            raw_token=raw_token,
            purpose=EmailTokenPurpose.VERIFY_EMAIL,
        )
        user = self.session.execute(select(User).where(User.id == email_token.user_id)).scalar_one()
        user.email_verified = True
        email_token.consumed_at = utc_now()
        self.session.commit()
        self.session.refresh(user)
        return user

    def resend_verification_email(self, *, email: str) -> None:
        email_normalized = normalize_email(email)
        user = self.user_repository.get_by_email_normalized(email_normalized)
        if user is None or user.email_verified is True:
            return

        self._consume_outstanding_email_tokens(user.id, EmailTokenPurpose.VERIFY_EMAIL)
        self._issue_email_token(user=user, purpose=EmailTokenPurpose.VERIFY_EMAIL)
        self.session.commit()

    def request_password_reset(self, *, email: str) -> None:
        email_normalized = normalize_email(email)
        user = self.user_repository.get_by_email_normalized(email_normalized)
        if user is None or not user.is_active:
            return

        self._consume_outstanding_email_tokens(user.id, EmailTokenPurpose.RESET_PASSWORD)
        self._issue_email_token(user=user, purpose=EmailTokenPurpose.RESET_PASSWORD)
        self.session.commit()

    def reset_password(self, *, raw_token: str, new_password: str) -> User:
        email_token = self._get_valid_email_token(
            raw_token=raw_token,
            purpose=EmailTokenPurpose.RESET_PASSWORD,
        )
        user = self.session.execute(select(User).where(User.id == email_token.user_id)).scalar_one()
        user.password_hash = hash_password(new_password)
        email_token.consumed_at = utc_now()

        refresh_sessions = self.session.execute(
            select(RefreshSession).where(
                RefreshSession.user_id == user.id,
                RefreshSession.revoked_at.is_(None),
            )
        ).scalars().all()
        now = utc_now()
        for refresh_session in refresh_sessions:
            refresh_session.revoked_at = now
            refresh_session.last_used_at = now

        self.session.commit()
        self.session.refresh(user)
        return user

    def _issue_session(self, *, user: User, device_name: str) -> LoginResult:
        player_account = user.player_account
        access_token, access_expires_at = build_access_token(user.id)
        raw_refresh_token = generate_opaque_token()
        refresh_expires_at = utc_now() + timedelta(days=self.settings.refresh_token_expire_days)

        refresh_session = RefreshSession(
            user_id=user.id,
            token_hash=hash_opaque_token(raw_refresh_token),
            device_name=device_name,
            issued_at=utc_now(),
            expires_at=refresh_expires_at,
            last_used_at=utc_now(),
        )
        self.session.add(refresh_session)
        self.session.commit()

        access_expires_in = int((access_expires_at - utc_now()).total_seconds())
        refresh_expires_in = int((refresh_expires_at - utc_now()).total_seconds())

        return LoginResult(
            access_token=access_token,
            access_expires_in=max(access_expires_in, 0),
            refresh_token=raw_refresh_token,
            refresh_expires_in=max(refresh_expires_in, 0),
            user=user,
            player_account=player_account,
        )

    def _issue_email_token(self, *, user: User, purpose: EmailTokenPurpose) -> EmailToken:
        raw_token = generate_opaque_token()
        email_token = EmailToken(
            user_id=user.id,
            purpose=purpose,
            token_hash=hash_opaque_token(raw_token),
            expires_at=utc_now() + timedelta(hours=self.settings.email_token_expire_hours),
        )
        self.session.add(email_token)
        self.session.flush()

        if purpose == EmailTokenPurpose.VERIFY_EMAIL:
            subject = "VoidRP: подтверждение почты"
            body = (
                "Добро пожаловать в VoidRP.\n\n"
                "На этом этапе сервис пока использует logging email backend.\n"
                f"Ваш verification token: {raw_token}\n"
            )
        else:
            subject = "VoidRP: сброс пароля"
            body = (
                "Вы запросили сброс пароля аккаунта VoidRP.\n\n"
                "На этом этапе сервис пока использует logging email backend.\n"
                f"Ваш reset token: {raw_token}\n"
            )

        self.email_service.send(
            EmailMessage(
                to_email=user.email,
                subject=subject,
                body=body,
            )
        )
        return email_token

    def _consume_outstanding_email_tokens(self, user_id, purpose: EmailTokenPurpose) -> None:
        outstanding_tokens = self.session.execute(
            select(EmailToken).where(
                EmailToken.user_id == user_id,
                EmailToken.purpose == purpose,
                EmailToken.consumed_at.is_(None),
            )
        ).scalars().all()

        now = utc_now()
        for token in outstanding_tokens:
            token.consumed_at = now

    def _get_valid_email_token(self, *, raw_token: str, purpose: EmailTokenPurpose) -> EmailToken:
        token_hash = hash_opaque_token(raw_token)
        email_token = self.session.execute(
            select(EmailToken).where(
                EmailToken.token_hash == token_hash,
                EmailToken.purpose == purpose,
            )
        ).scalar_one_or_none()

        if email_token is None:
            raise TokenValidationError("token is invalid")

        if email_token.consumed_at is not None:
            raise TokenValidationError("token is already used")

        if email_token.expires_at <= utc_now():
            raise TokenValidationError("token is expired")

        return email_token

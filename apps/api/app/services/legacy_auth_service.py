from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from uuid import UUID

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from apps.api.app.core.security import verify_password
from apps.api.app.models.player_account import PlayerAccount
from apps.api.app.models.user import User
from apps.api.app.utils.normalization import normalize_minecraft_nickname


class LegacyAuthError(Exception):
    pass


class LegacyAuthValidationError(LegacyAuthError):
    pass


@dataclass(slots=True)
class LegacyLoginResult:
    user_id: UUID
    minecraft_nickname: str
    legacy_auth_enabled: bool
    email_verified: bool


class LegacyAuthService:
    _crypt_context = CryptContext(
        schemes=[
            "bcrypt",
            "argon2",
            "sha256_crypt",
            "sha512_crypt",
            "pbkdf2_sha256",
            "pbkdf2_sha512",
            "phpass",
            "md5_crypt",
            "des_crypt",
        ],
        deprecated="auto",
    )

    def __init__(self, session: Session) -> None:
        self.session = session

    def legacy_login(self, *, player_name: str, password: str) -> LegacyLoginResult:
        raw_player_name, normalized_player_name = normalize_minecraft_nickname(player_name)

        player_account = self.session.execute(
            select(PlayerAccount)
            .options(joinedload(PlayerAccount.user))
            .where(PlayerAccount.minecraft_nickname_normalized == normalized_player_name)
        ).unique().scalar_one_or_none()

        if player_account is None or player_account.user is None:
            raise LegacyAuthValidationError("player account was not found")

        user = player_account.user

        if not user.is_active:
            raise LegacyAuthValidationError("account is disabled")

        if not player_account.legacy_auth_enabled:
            raise LegacyAuthValidationError("legacy auth is disabled for this account")

        if not self._verify_legacy_password(player_account, password):
            raise LegacyAuthValidationError("invalid credentials")

        return LegacyLoginResult(
            user_id=user.id,
            minecraft_nickname=raw_player_name,
            legacy_auth_enabled=player_account.legacy_auth_enabled,
            email_verified=user.email_verified,
        )

    def _verify_legacy_password(self, player_account: PlayerAccount, password: str) -> bool:
        legacy_hash = player_account.legacy_password_hash
        legacy_algo = (player_account.legacy_hash_algo or "").strip().lower()

        if not legacy_hash:
            return False

        if legacy_algo in {"sha256_hex", "sha256"}:
            candidate = hashlib.sha256(password.encode("utf-8")).hexdigest()
            return hmac.compare_digest(candidate, legacy_hash)

        if legacy_algo in {"argon2id", "pwdlib_argon2id", "current_password_hash"}:
            try:
                return verify_password(password, legacy_hash)
            except Exception:
                return False

        try:
            return self._crypt_context.verify(password, legacy_hash)
        except Exception:
            return False
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from apps.api.app.schemas.common import ORMModel


class PlayerAccountRead(ORMModel):
    id: UUID
    minecraft_nickname: str
    nickname_locked: bool
    legacy_auth_enabled: bool


class UserRead(ORMModel):
    id: UUID
    site_login: str
    email: str
    email_verified: bool
    is_active: bool
    created_at: datetime


class MeResponse(ORMModel):
    user: UserRead
    player_account: PlayerAccountRead

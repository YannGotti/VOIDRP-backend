from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class LegacyLoginRequest(BaseModel):
    player_name: str = Field(min_length=3, max_length=16)
    password: str = Field(min_length=1, max_length=256)


class LegacyLoginResponse(BaseModel):
    accepted: bool = True
    user_id: UUID
    minecraft_nickname: str
    legacy_auth_enabled: bool
    email_verified: bool

from pydantic import BaseModel


class PlayerAccessRequest(BaseModel):
    player_name: str


class PlayerAccessResponse(BaseModel):
    player_exists: bool
    user_active: bool
    legacy_auth_enabled: bool
    must_use_launcher: bool
    minecraft_nickname: str | None = None
    error: str | None = None
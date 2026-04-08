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
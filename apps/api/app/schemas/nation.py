from __future__ import annotations

import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

NATION_SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,63}$")
ACCENT_COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")


class NationAssetsRead(BaseModel):
    icon_url: str | None = None
    icon_preview_url: str | None = None
    banner_url: str | None = None
    banner_preview_url: str | None = None
    background_url: str | None = None
    background_preview_url: str | None = None


class NationStatsRead(BaseModel):
    members_count: int
    pending_requests_count: int


class NationMemberRead(BaseModel):
    user_id: UUID
    site_login: str
    minecraft_nickname: str | None = None
    role: str
    created_at: datetime


class NationJoinRequestRead(BaseModel):
    id: UUID
    user_id: UUID
    site_login: str
    minecraft_nickname: str | None = None
    message: str | None = None
    status: str
    created_at: datetime


class NationRead(BaseModel):
    id: UUID
    slug: str
    title: str
    tag: str
    short_description: str | None = None
    description: str | None = None
    accent_color: str | None = None
    recruitment_policy: str
    is_public: bool
    leader_user_id: UUID
    assets: NationAssetsRead
    stats: NationStatsRead
    viewer_role: str | None = None
    viewer_is_member: bool
    viewer_can_manage: bool
    viewer_request_status: str | None = None
    members: list[NationMemberRead]
    join_requests: list[NationJoinRequestRead]
    created_at: datetime
    updated_at: datetime


class NationListResponse(BaseModel):
    total: int
    items: list[NationRead]


class NationCreateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=64)
    slug: str = Field(min_length=3, max_length=64)
    tag: str = Field(min_length=2, max_length=8)
    short_description: str | None = Field(default=None, max_length=140)
    description: str | None = Field(default=None, max_length=5000)
    accent_color: str | None = Field(default="#6d5df6", max_length=7)
    recruitment_policy: str = Field(default="request", pattern="^(open|request|invite_only)$")
    is_public: bool = True

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str) -> str:
        value = value.strip().lower()
        if not NATION_SLUG_PATTERN.fullmatch(value):
            raise ValueError("nation slug contains invalid characters")
        return value

    @field_validator("tag")
    @classmethod
    def validate_tag(cls, value: str) -> str:
        value = value.strip().upper()
        if len(value) < 2 or len(value) > 8:
            raise ValueError("nation tag must be between 2 and 8 characters")
        return value

    @field_validator("accent_color")
    @classmethod
    def validate_accent_color(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        if not ACCENT_COLOR_PATTERN.fullmatch(value):
            raise ValueError("accent_color must be in #RRGGBB format")
        return value


class NationUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=64)
    slug: str | None = Field(default=None, min_length=3, max_length=64)
    tag: str | None = Field(default=None, min_length=2, max_length=8)
    short_description: str | None = Field(default=None, max_length=140)
    description: str | None = Field(default=None, max_length=5000)
    accent_color: str | None = Field(default=None, max_length=7)
    recruitment_policy: str | None = Field(default=None, pattern="^(open|request|invite_only)$")
    is_public: bool | None = None

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip().lower()
        if not NATION_SLUG_PATTERN.fullmatch(value):
            raise ValueError("nation slug contains invalid characters")
        return value

    @field_validator("tag")
    @classmethod
    def validate_tag(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip().upper()
        if len(value) < 2 or len(value) > 8:
            raise ValueError("nation tag must be between 2 and 8 characters")
        return value

    @field_validator("accent_color")
    @classmethod
    def validate_accent_color(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        if not ACCENT_COLOR_PATTERN.fullmatch(value):
            raise ValueError("accent_color must be in #RRGGBB format")
        return value


class NationJoinRequestCreate(BaseModel):
    message: str | None = Field(default=None, max_length=500)


class NationJoinActionResponse(BaseModel):
    message: str
    nation: NationRead | None


class NationDeleteAssetResponse(BaseModel):
    message: str
    nation: NationRead


class NationAssetUploadResponse(BaseModel):
    message: str
    nation: NationRead

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


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
    viewer_is_member: bool = False
    viewer_can_manage: bool = False
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
    description: str | None = None
    accent_color: str | None = Field(default=None, max_length=7)
    recruitment_policy: str = Field(default='request')
    is_public: bool = True


class NationUpdateRequest(BaseModel):
    slug: str | None = Field(default=None, min_length=3, max_length=64)
    title: str | None = Field(default=None, min_length=3, max_length=64)
    tag: str | None = Field(default=None, min_length=2, max_length=8)
    short_description: str | None = Field(default=None, max_length=140)
    description: str | None = None
    accent_color: str | None = Field(default=None, max_length=7)
    recruitment_policy: str | None = Field(default=None)
    is_public: bool | None = None


class NationJoinRequestCreate(BaseModel):
    message: str | None = Field(default=None, max_length=600)


class NationJoinActionResponse(BaseModel):
    message: str
    nation: NationRead


class NationMemberRoleUpdateRequest(BaseModel):
    role: str = Field(pattern='^(officer|member)$')


class NationTransferLeadershipRequest(BaseModel):
    target_user_id: UUID


class NationActionResponse(BaseModel):
    message: str
    nation: NationRead

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class NationStatsPayload(BaseModel):
    treasury_balance: float = 0
    territory_points: int = 0
    total_playtime_minutes: int = 0
    pvp_kills: int = 0
    mob_kills: int = 0
    boss_kills: int = 0
    deaths: int = 0
    blocks_placed: int = 0
    blocks_broken: int = 0
    events_completed: int = 0
    prestige_score: int = 0


class NationStatsRead(NationStatsPayload):
    nation_id: UUID
    updated_at: datetime


class NationRankingItemRead(BaseModel):
    nation_id: UUID
    slug: str
    title: str
    tag: str
    accent_color: str | None = None
    banner_url: str | None = None
    icon_url: str | None = None
    members_count: int = 0
    treasury_balance: float = 0
    territory_points: int = 0
    total_playtime_minutes: int = 0
    pvp_kills: int = 0
    mob_kills: int = 0
    prestige_score: int = 0
    score: float = 0


class NationRankingResponse(BaseModel):
    items: list[NationRankingItemRead]


class NationStatsUpsertRequest(BaseModel):
    nation_slug: str = Field(min_length=3, max_length=64)
    treasury_balance: float = 0
    territory_points: int = 0
    total_playtime_minutes: int = 0
    pvp_kills: int = 0
    mob_kills: int = 0
    boss_kills: int = 0
    deaths: int = 0
    blocks_placed: int = 0
    blocks_broken: int = 0
    events_completed: int = 0
    prestige_score: int = 0


class NationStatsUpsertResponse(BaseModel):
    message: str
    nation_id: UUID
    nation_slug: str
    updated_at: datetime

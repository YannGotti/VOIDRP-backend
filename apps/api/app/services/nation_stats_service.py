from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.app.models.nation import Nation
from apps.api.app.models.nation_member import NationMember
from apps.api.app.models.nation_stat import NationStat
from apps.api.app.schemas.nation_stats import (
    NationRankingItemRead,
    NationRankingResponse,
    NationStatsRead,
    NationStatsUpsertRequest,
    NationStatsUpsertResponse,
)
from apps.api.app.services.nation_service import NationNotFoundError


class NationStatsService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_stats_by_slug(self, slug: str) -> NationStatsRead:
        nation = self.session.execute(select(Nation).where(Nation.slug == slug)).scalar_one_or_none()
        if nation is None:
            raise NationNotFoundError("nation was not found")

        stat = self._get_or_create_for_nation(nation)
        self.session.commit()
        self.session.refresh(stat)

        return NationStatsRead(
            nation_id=stat.nation_id,
            treasury_balance=float(stat.treasury_balance or 0),
            territory_points=stat.territory_points,
            total_playtime_minutes=stat.total_playtime_minutes,
            pvp_kills=stat.pvp_kills,
            mob_kills=stat.mob_kills,
            boss_kills=stat.boss_kills,
            deaths=stat.deaths,
            blocks_placed=stat.blocks_placed,
            blocks_broken=stat.blocks_broken,
            events_completed=stat.events_completed,
            prestige_score=stat.prestige_score,
            updated_at=stat.updated_at,
        )

    def upsert_from_game(self, payload: NationStatsUpsertRequest) -> NationStatsUpsertResponse:
        nation = self.session.execute(select(Nation).where(Nation.slug == payload.nation_slug)).scalar_one_or_none()
        if nation is None:
            raise NationNotFoundError("nation was not found")

        stat = self._get_or_create_for_nation(nation)
        stat.treasury_balance = payload.treasury_balance
        stat.territory_points = payload.territory_points
        stat.total_playtime_minutes = payload.total_playtime_minutes
        stat.pvp_kills = payload.pvp_kills
        stat.mob_kills = payload.mob_kills
        stat.boss_kills = payload.boss_kills
        stat.deaths = payload.deaths
        stat.blocks_placed = payload.blocks_placed
        stat.blocks_broken = payload.blocks_broken
        stat.events_completed = payload.events_completed
        stat.prestige_score = payload.prestige_score

        self.session.commit()
        self.session.refresh(stat)

        return NationStatsUpsertResponse(
            message="Nation stats updated successfully.",
            nation_id=nation.id,
            nation_slug=nation.slug,
            updated_at=stat.updated_at,
        )

    def get_rankings(self) -> NationRankingResponse:
        nations = self.session.execute(
            select(Nation).where(Nation.is_public.is_(True)).order_by(Nation.created_at.desc())
        ).scalars().all()

        items: list[NationRankingItemRead] = []
        for nation in nations:
            stat = self.session.execute(select(NationStat).where(NationStat.nation_id == nation.id)).scalar_one_or_none()
            members_count = int(self.session.query(NationMember).filter(NationMember.nation_id == nation.id).count())

            treasury = float(stat.treasury_balance) if stat else 0.0
            territory = stat.territory_points if stat else 0
            playtime = stat.total_playtime_minutes if stat else 0
            pvp = stat.pvp_kills if stat else 0
            mob = stat.mob_kills if stat else 0
            prestige = stat.prestige_score if stat else 0

            score = (
                treasury * 0.002
                + territory * 15
                + playtime * 0.05
                + pvp * 8
                + mob * 0.2
                + prestige
                + members_count * 10
            )

            items.append(
                NationRankingItemRead(
                    nation_id=nation.id,
                    slug=nation.slug,
                    title=nation.title,
                    tag=nation.tag,
                    accent_color=nation.accent_color,
                    banner_url=nation.banner_url or nation.banner_preview_url,
                    icon_url=nation.icon_url or nation.icon_preview_url,
                    members_count=members_count,
                    treasury_balance=treasury,
                    territory_points=territory,
                    total_playtime_minutes=playtime,
                    pvp_kills=pvp,
                    mob_kills=mob,
                    prestige_score=prestige,
                    score=round(score, 2),
                )
            )

        items.sort(key=lambda x: x.score, reverse=True)
        return NationRankingResponse(items=items)

    def _get_or_create_for_nation(self, nation: Nation) -> NationStat:
        stat = self.session.execute(select(NationStat).where(NationStat.nation_id == nation.id)).scalar_one_or_none()
        if stat is None:
            stat = NationStat(nation_id=nation.id)
            self.session.add(stat)
            self.session.flush()
        return stat

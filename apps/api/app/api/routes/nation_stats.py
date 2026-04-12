from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from apps.api.app.config import get_settings
from apps.api.app.db import get_db_session
from apps.api.app.schemas.nation_stats import (
    NationRankingResponse,
    NationStatsRead,
    NationStatsUpsertRequest,
    NationStatsUpsertResponse,
)
from apps.api.app.services.nation_service import NationNotFoundError
from apps.api.app.services.nation_stats_service import NationStatsService

router = APIRouter(prefix="/nation-stats", tags=["nation-stats"])


def get_nation_stats_service(session: Annotated[Session, Depends(get_db_session)]) -> NationStatsService:
    return NationStatsService(session=session)


@router.get("/rankings", response_model=NationRankingResponse)
def get_nation_rankings(service: Annotated[NationStatsService, Depends(get_nation_stats_service)]) -> NationRankingResponse:
    return service.get_rankings()


@router.get("/nations/{slug}", response_model=NationStatsRead)
def get_nation_stats_by_slug(slug: str, service: Annotated[NationStatsService, Depends(get_nation_stats_service)]) -> NationStatsRead:
    try:
        return service.get_stats_by_slug(slug)
    except NationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/internal/upsert", response_model=NationStatsUpsertResponse)
def upsert_nation_stats_from_game(
    payload: NationStatsUpsertRequest,
    x_game_auth_secret: Annotated[str | None, Header()] = None,
    service: Annotated[NationStatsService, Depends(get_nation_stats_service)] = None,
) -> NationStatsUpsertResponse:
    settings = get_settings()
    if not x_game_auth_secret or x_game_auth_secret != settings.game_auth_shared_secret:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid game auth secret")

    try:
        return service.upsert_from_game(payload)
    except NationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

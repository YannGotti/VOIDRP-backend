from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from apps.api.app.db import get_db_session
from apps.api.app.dependencies.server_auth import require_game_auth_secret
from apps.api.app.schemas.server_auth import (
    LegacyLoginRequest,
    LegacyLoginResponse,
    PlayerAccessRequest,
    PlayerAccessResponse,
)

from apps.api.app.services.legacy_auth_service import LegacyAuthService, LegacyAuthValidationError
from apps.api.app.services.server_player_access_service import ServerPlayerAccessService

router = APIRouter(
    prefix="/server/auth",
    tags=["server-auth"],
    dependencies=[Depends(require_game_auth_secret)],
)


def get_legacy_auth_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> LegacyAuthService:
    return LegacyAuthService(session=session)


@router.post("/legacy-login", response_model=LegacyLoginResponse)
def legacy_login(
    payload: LegacyLoginRequest,
    service: Annotated[LegacyAuthService, Depends(get_legacy_auth_service)],
) -> LegacyLoginResponse:
    try:
        result = service.legacy_login(
            player_name=payload.player_name,
            password=payload.password,
        )
    except LegacyAuthValidationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    return LegacyLoginResponse(
        user_id=result.user_id,
        minecraft_nickname=result.minecraft_nickname,
        legacy_auth_enabled=result.legacy_auth_enabled,
        email_verified=result.email_verified,
    )

@router.post("/player-access", response_model=PlayerAccessResponse)
def player_access(
    payload: PlayerAccessRequest,
    _: None = Depends(require_game_auth_secret),
    session: Session = Depends(get_db_session),
) -> PlayerAccessResponse:
    service = ServerPlayerAccessService(session)
    result = service.get_player_access(player_name=payload.player_name)

    return PlayerAccessResponse(
        player_exists=result.player_exists,
        user_active=result.user_active,
        legacy_auth_enabled=result.legacy_auth_enabled,
        must_use_launcher=result.must_use_launcher,
        minecraft_nickname=result.minecraft_nickname,
        error=result.error,
    )
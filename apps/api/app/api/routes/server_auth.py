from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from apps.api.app.db import get_db_session
from apps.api.app.dependencies.server_auth import require_game_auth_secret
from apps.api.app.schemas.server_auth import LegacyLoginRequest, LegacyLoginResponse
from apps.api.app.services.legacy_auth_service import LegacyAuthService, LegacyAuthValidationError

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
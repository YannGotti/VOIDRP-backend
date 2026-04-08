from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.app.db import get_db_session
from apps.api.app.dependencies.auth import get_current_user
from apps.api.app.models.player_account import PlayerAccount
from apps.api.app.models.user import User
from apps.api.app.schemas.account import MeResponse

router = APIRouter(tags=["account"])


@router.get("/me", response_model=MeResponse)
def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db_session)],
) -> MeResponse:
    player_account = session.execute(
        select(PlayerAccount).where(PlayerAccount.user_id == current_user.id)
    ).scalar_one()

    return MeResponse(user=current_user, player_account=player_account)

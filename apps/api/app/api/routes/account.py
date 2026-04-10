from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from apps.api.app.core.security import hash_opaque_token, utc_now
from apps.api.app.db import get_db_session
from apps.api.app.dependencies.auth import get_current_user
from apps.api.app.models.player_account import PlayerAccount
from apps.api.app.models.refresh_session import RefreshSession
from apps.api.app.models.user import User
from apps.api.app.schemas.account import (
    AccountSecurityRead,
    MeResponse,
    RevokeOtherSessionsRequest,
    RevokeSessionsResponse,
)

router = APIRouter(tags=["account"])


def _get_player_account(*, session: Session, user_id) -> PlayerAccount:
    return session.execute(
        select(PlayerAccount).where(PlayerAccount.user_id == user_id)
    ).scalar_one()


def _build_me_response(
    *,
    session: Session,
    current_user: User,
    player_account: PlayerAccount,
) -> MeResponse:
    now = utc_now()

    active_refresh_sessions = int(
        session.scalar(
            select(func.count())
            .select_from(RefreshSession)
            .where(
                RefreshSession.user_id == current_user.id,
                RefreshSession.revoked_at.is_(None),
                RefreshSession.expires_at > now,
            )
        )
        or 0
    )

    legacy_hash_present = bool(player_account.legacy_password_hash)
    legacy_ready = bool(
        player_account.legacy_auth_enabled
        and player_account.legacy_password_hash
        and player_account.legacy_hash_algo
    )

    return MeResponse(
        user=current_user,
        player_account=player_account,
        security=AccountSecurityRead(
            active_refresh_sessions=active_refresh_sessions,
            must_use_launcher=bool(current_user.is_active and not player_account.legacy_auth_enabled),
            legacy_hash_present=legacy_hash_present,
            legacy_ready=legacy_ready,
        ),
    )


@router.get("/me", response_model=MeResponse)
def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db_session)],
) -> MeResponse:
    player_account = _get_player_account(session=session, user_id=current_user.id)
    return _build_me_response(
        session=session,
        current_user=current_user,
        player_account=player_account,
    )


@router.post("/account/revoke-other-sessions", response_model=RevokeSessionsResponse)
def revoke_other_sessions(
    payload: RevokeOtherSessionsRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db_session)],
) -> RevokeSessionsResponse:
    current_refresh_token_hash = hash_opaque_token(payload.refresh_token)
    now = utc_now()

    refresh_sessions = session.execute(
        select(RefreshSession).where(
            RefreshSession.user_id == current_user.id,
            RefreshSession.revoked_at.is_(None),
            RefreshSession.expires_at > now,
            RefreshSession.token_hash != current_refresh_token_hash,
        )
    ).scalars().all()

    revoked_sessions = 0
    for refresh_session in refresh_sessions:
        refresh_session.revoked_at = now
        refresh_session.last_used_at = now
        revoked_sessions += 1

    session.commit()

    return RevokeSessionsResponse(
        message="Other active sessions revoked successfully.",
        revoked_sessions=revoked_sessions,
    )
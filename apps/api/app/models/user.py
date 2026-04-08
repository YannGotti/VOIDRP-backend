from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.api.app.models.base import Base, TimestampMixin, UuidPrimaryKeyMixin

if TYPE_CHECKING:
    from apps.api.app.models.email_token import EmailToken
    from apps.api.app.models.player_account import PlayerAccount
    from apps.api.app.models.refresh_session import RefreshSession


class User(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    site_login: Mapped[str] = mapped_column(String(32), nullable=False)
    site_login_normalized: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    email_normalized: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)

    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    player_account: Mapped["PlayerAccount"] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    refresh_sessions: Mapped[list["RefreshSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    email_tokens: Mapped[list["EmailToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

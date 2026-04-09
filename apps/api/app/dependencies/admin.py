from __future__ import annotations

from typing import Annotated

from fastapi import Header, HTTPException, status

from apps.api.app.config import get_settings


def require_admin_api_secret(
    x_admin_api_secret: Annotated[str | None, Header(alias="X-Admin-Api-Secret")] = None,
) -> None:
    settings = get_settings()
    if not x_admin_api_secret or x_admin_api_secret != settings.admin_api_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin api secret",
        )
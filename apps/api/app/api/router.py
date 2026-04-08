from __future__ import annotations

from fastapi import APIRouter

from apps.api.app.api.routes.account import router as account_router
from apps.api.app.api.routes.auth import router as auth_router
from apps.api.app.api.routes.health import router as health_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(account_router)

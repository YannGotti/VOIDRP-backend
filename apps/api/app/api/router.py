from __future__ import annotations

from fastapi import APIRouter

from apps.api.app.api.routes.account import router as account_router
from apps.api.app.api.routes.admin import router as admin_router
from apps.api.app.api.routes.auth import router as auth_router
from apps.api.app.api.routes.health import router as health_router
from apps.api.app.api.routes.nations import router as nations_router
from apps.api.app.api.routes.nation_stats import router as nation_stats_router
from apps.api.app.api.routes.play_ticket import launcher_router as launcher_router
from apps.api.app.api.routes.play_ticket import server_router as server_auth_ticket_router
from apps.api.app.api.routes.profiles import router as profiles_router
from apps.api.app.api.routes.referrals import router as referrals_router
from apps.api.app.api.routes.server_auth import router as server_auth_router
from apps.api.app.api.routes.social import router as social_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(account_router)
api_router.include_router(launcher_router)
api_router.include_router(server_auth_ticket_router)
api_router.include_router(server_auth_router)
api_router.include_router(admin_router)
api_router.include_router(profiles_router)
api_router.include_router(social_router)
api_router.include_router(referrals_router)
api_router.include_router(nations_router)
api_router.include_router(nation_stats_router)

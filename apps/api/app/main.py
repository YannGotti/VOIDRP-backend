from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from apps.api.app.api.router import api_router
from apps.api.app.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()

    os.makedirs(settings.media_storage_root, exist_ok=True)

    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        version="0.2.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.mount(
        settings.media_public_mount_path,
        StaticFiles(directory=settings.media_storage_root),
        name="media",
    )

    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
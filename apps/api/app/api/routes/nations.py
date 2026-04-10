from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from apps.api.app.db import get_db_session
from apps.api.app.dependencies.auth import get_current_user, get_optional_current_user
from apps.api.app.models.user import User
from apps.api.app.schemas.nation import (
    NationAssetUploadResponse,
    NationCreateRequest,
    NationDeleteAssetResponse,
    NationJoinActionResponse,
    NationJoinRequestCreate,
    NationListResponse,
    NationRead,
    NationUpdateRequest,
)
from apps.api.app.services.nation_media_service import NationMediaService, NationMediaValidationError
from apps.api.app.services.nation_service import NationConflictError, NationNotFoundError, NationPermissionError, NationService, NationValidationError

router = APIRouter(prefix="/nations", tags=["nations"])


def get_nation_service(session: Annotated[Session, Depends(get_db_session)]) -> NationService:
    return NationService(session=session)


def get_nation_media_service(session: Annotated[Session, Depends(get_db_session)]) -> NationMediaService:
    return NationMediaService(session=session)


@router.get("", response_model=NationListResponse)
def list_nations(viewer: Annotated[User | None, Depends(get_optional_current_user)], service: Annotated[NationService, Depends(get_nation_service)]) -> NationListResponse:
    return service.list_public(viewer=viewer)


@router.get("/me", response_model=NationRead | None)
def get_my_nation(current_user: Annotated[User, Depends(get_current_user)], service: Annotated[NationService, Depends(get_nation_service)]) -> NationRead | None:
    return service.get_my_nation(current_user)


@router.post("", response_model=NationRead)
def create_nation(payload: NationCreateRequest, current_user: Annotated[User, Depends(get_current_user)], service: Annotated[NationService, Depends(get_nation_service)]) -> NationRead:
    try:
        return service.create(current_user, payload)
    except (NationConflictError, NationValidationError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.patch("/me", response_model=NationRead)
def update_my_nation(payload: NationUpdateRequest, current_user: Annotated[User, Depends(get_current_user)], service: Annotated[NationService, Depends(get_nation_service)]) -> NationRead:
    try:
        return service.update_my_nation(current_user, payload)
    except NationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (NationConflictError, NationValidationError, NationPermissionError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/me/leave", response_model=NationJoinActionResponse)
def leave_my_nation(current_user: Annotated[User, Depends(get_current_user)], service: Annotated[NationService, Depends(get_nation_service)]) -> NationJoinActionResponse:
    try:
        service.leave_my_nation(current_user)
        return NationJoinActionResponse(message="Nation leave action completed.", nation=service.get_my_nation(current_user))
    except NationValidationError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("/{slug}", response_model=NationRead)
def get_public_nation(slug: str, viewer: Annotated[User | None, Depends(get_optional_current_user)], service: Annotated[NationService, Depends(get_nation_service)]) -> NationRead:
    try:
        return service.get_by_slug(slug, viewer=viewer)
    except NationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/{slug}/join", response_model=NationJoinActionResponse)
def create_join_request(slug: str, payload: NationJoinRequestCreate, current_user: Annotated[User, Depends(get_current_user)], service: Annotated[NationService, Depends(get_nation_service)]) -> NationJoinActionResponse:
    try:
        return service.create_join_request(current_user, slug, payload)
    except NationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (NationConflictError, NationValidationError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/{slug}/requests/{request_id}/approve", response_model=NationRead)
def approve_join_request(slug: str, request_id: UUID, current_user: Annotated[User, Depends(get_current_user)], service: Annotated[NationService, Depends(get_nation_service)]) -> NationRead:
    try:
        return service.approve_request(current_user, slug, request_id)
    except NationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (NationConflictError, NationValidationError, NationPermissionError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/{slug}/requests/{request_id}/reject", response_model=NationRead)
def reject_join_request(slug: str, request_id: UUID, current_user: Annotated[User, Depends(get_current_user)], service: Annotated[NationService, Depends(get_nation_service)]) -> NationRead:
    try:
        return service.reject_request(current_user, slug, request_id)
    except NationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (NationConflictError, NationValidationError, NationPermissionError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/me/icon", response_model=NationAssetUploadResponse)
async def upload_nation_icon(file: UploadFile = File(...), current_user: Annotated[User, Depends(get_current_user)] = None, media_service: Annotated[NationMediaService, Depends(get_nation_media_service)] = None, nation_service: Annotated[NationService, Depends(get_nation_service)] = None) -> NationAssetUploadResponse:
    try:
        nation = await media_service.save_nation_asset(current_user=current_user, slot="icon", upload=file)
        return NationAssetUploadResponse(message="Nation icon uploaded successfully.", nation=nation_service.get_by_slug(nation.slug, viewer=current_user))
    except (NationMediaValidationError, NationPermissionError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.delete("/me/icon", response_model=NationDeleteAssetResponse)
def delete_nation_icon(current_user: Annotated[User, Depends(get_current_user)], media_service: Annotated[NationMediaService, Depends(get_nation_media_service)], nation_service: Annotated[NationService, Depends(get_nation_service)]) -> NationDeleteAssetResponse:
    try:
        nation = media_service.delete_nation_asset(current_user=current_user, slot="icon")
        return NationDeleteAssetResponse(message="Nation icon deleted successfully.", nation=nation_service.get_by_slug(nation.slug, viewer=current_user))
    except (NationMediaValidationError, NationPermissionError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.post("/me/banner", response_model=NationAssetUploadResponse)
async def upload_nation_banner(file: UploadFile = File(...), current_user: Annotated[User, Depends(get_current_user)] = None, media_service: Annotated[NationMediaService, Depends(get_nation_media_service)] = None, nation_service: Annotated[NationService, Depends(get_nation_service)] = None) -> NationAssetUploadResponse:
    try:
        nation = await media_service.save_nation_asset(current_user=current_user, slot="banner", upload=file)
        return NationAssetUploadResponse(message="Nation banner uploaded successfully.", nation=nation_service.get_by_slug(nation.slug, viewer=current_user))
    except (NationMediaValidationError, NationPermissionError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.delete("/me/banner", response_model=NationDeleteAssetResponse)
def delete_nation_banner(current_user: Annotated[User, Depends(get_current_user)], media_service: Annotated[NationMediaService, Depends(get_nation_media_service)], nation_service: Annotated[NationService, Depends(get_nation_service)]) -> NationDeleteAssetResponse:
    try:
        nation = media_service.delete_nation_asset(current_user=current_user, slot="banner")
        return NationDeleteAssetResponse(message="Nation banner deleted successfully.", nation=nation_service.get_by_slug(nation.slug, viewer=current_user))
    except (NationMediaValidationError, NationPermissionError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.post("/me/background", response_model=NationAssetUploadResponse)
async def upload_nation_background(file: UploadFile = File(...), current_user: Annotated[User, Depends(get_current_user)] = None, media_service: Annotated[NationMediaService, Depends(get_nation_media_service)] = None, nation_service: Annotated[NationService, Depends(get_nation_service)] = None) -> NationAssetUploadResponse:
    try:
        nation = await media_service.save_nation_asset(current_user=current_user, slot="background", upload=file)
        return NationAssetUploadResponse(message="Nation background uploaded successfully.", nation=nation_service.get_by_slug(nation.slug, viewer=current_user))
    except (NationMediaValidationError, NationPermissionError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.delete("/me/background", response_model=NationDeleteAssetResponse)
def delete_nation_background(current_user: Annotated[User, Depends(get_current_user)], media_service: Annotated[NationMediaService, Depends(get_nation_media_service)], nation_service: Annotated[NationService, Depends(get_nation_service)]) -> NationDeleteAssetResponse:
    try:
        nation = media_service.delete_nation_asset(current_user=current_user, slot="background")
        return NationDeleteAssetResponse(message="Nation background deleted successfully.", nation=nation_service.get_by_slug(nation.slug, viewer=current_user))
    except (NationMediaValidationError, NationPermissionError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

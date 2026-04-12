from __future__ import annotations

import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from apps.api.app.models.nation import Nation
from apps.api.app.models.nation_join_request import NationJoinRequest
from apps.api.app.models.nation_member import NationMember
from apps.api.app.models.user import User
from apps.api.app.schemas.nation import (
    NationActionResponse,
    NationAssetsRead,
    NationCreateRequest,
    NationJoinActionResponse,
    NationJoinRequestCreate,
    NationJoinRequestRead,
    NationListResponse,
    NationMemberRead,
    NationMemberRoleUpdateRequest,
    NationRead,
    NationStatsRead,
    NationTransferLeadershipRequest,
    NationUpdateRequest,
)

SLUG_CLEANUP_PATTERN = re.compile(r"[^a-z0-9._-]+")


class NationNotFoundError(Exception): ...
class NationConflictError(Exception): ...
class NationPermissionError(Exception): ...
class NationValidationError(Exception): ...


class NationService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_public(self, viewer: User | None = None) -> NationListResponse:
        nations = (
            self.session.execute(
                select(Nation)
                .options(
                    joinedload(Nation.members).joinedload(NationMember.user).joinedload(User.player_account),
                    joinedload(Nation.join_requests).joinedload(NationJoinRequest.user).joinedload(User.player_account),
                )
                .where(Nation.is_public.is_(True))
                .order_by(Nation.created_at.desc())
            )
            .unique()
            .scalars()
            .all()
        )
        return NationListResponse(total=len(nations), items=[self._build_read(n, viewer=viewer) for n in nations])

    def get_my_nation(self, current_user: User) -> NationRead | None:
        nation = self._find_nation_for_user(current_user.id)
        return None if nation is None else self._build_read(nation, viewer=current_user)

    def get_by_slug(self, slug: str, viewer: User | None = None) -> NationRead:
        nation = self._get_nation_by_slug(slug)
        if nation is None:
            raise NationNotFoundError("nation was not found")
        if not nation.is_public and not self._can_manage(nation, viewer):
            raise NationNotFoundError("nation was not found")
        return self._build_read(nation, viewer=viewer)

    def create(self, current_user: User, payload: NationCreateRequest) -> NationRead:
        if self._find_nation_for_user(current_user.id) is not None:
            raise NationConflictError("user is already in a nation")
        slug = self._normalize_slug(payload.slug)
        if self._slug_exists(slug):
            raise NationConflictError("nation slug is already taken")
        nation = Nation(
            slug=slug,
            title=payload.title.strip(),
            tag=payload.tag.strip().upper(),
            short_description=(payload.short_description or "").strip() or None,
            description=(payload.description or "").strip() or None,
            accent_color=(payload.accent_color or "").strip() or None,
            recruitment_policy=payload.recruitment_policy,
            is_public=payload.is_public,
            leader_user_id=current_user.id,
            created_by_user_id=current_user.id,
        )
        self.session.add(nation)
        self.session.flush()
        self.session.add(NationMember(nation_id=nation.id, user_id=current_user.id, role="leader"))
        self.session.commit()
        return self.get_by_slug(nation.slug, viewer=current_user)

    def update_my_nation(self, current_user: User, payload: NationUpdateRequest) -> NationRead:
        nation = self._require_manageable_nation(current_user)
        fields_set = getattr(payload, "model_fields_set", set())
        if "slug" in fields_set and payload.slug is not None:
            normalized_slug = self._normalize_slug(payload.slug)
            existing = self._get_nation_by_slug(normalized_slug)
            if existing is not None and existing.id != nation.id:
                raise NationConflictError("nation slug is already taken")
            nation.slug = normalized_slug
        if "title" in fields_set and payload.title is not None:
            nation.title = payload.title.strip()
        if "tag" in fields_set and payload.tag is not None:
            nation.tag = payload.tag.strip().upper()
        if "short_description" in fields_set:
            nation.short_description = (payload.short_description or "").strip() or None
        if "description" in fields_set:
            nation.description = (payload.description or "").strip() or None
        if "accent_color" in fields_set:
            nation.accent_color = (payload.accent_color or "").strip() or None
        if "recruitment_policy" in fields_set and payload.recruitment_policy is not None:
            nation.recruitment_policy = payload.recruitment_policy
        if "is_public" in fields_set and payload.is_public is not None:
            nation.is_public = payload.is_public
        self.session.commit()
        return self.get_by_slug(nation.slug, viewer=current_user)

    def leave_my_nation(self, current_user: User) -> None:
        nation = self._find_nation_for_user(current_user.id)
        if nation is None:
            raise NationValidationError("user is not in a nation")
        membership = self._get_membership(nation.id, current_user.id)
        if membership is None:
            raise NationValidationError("membership was not found")
        if membership.role == "leader":
            if len(nation.members) > 1:
                raise NationValidationError("leader cannot leave while other members are still in the nation")
            self.session.delete(nation)
            self.session.commit()
            return
        self.session.delete(membership)
        self.session.commit()

    def create_join_request(self, current_user: User, slug: str, payload: NationJoinRequestCreate) -> NationJoinActionResponse:
        if self._find_nation_for_user(current_user.id) is not None:
            raise NationConflictError("user is already in a nation")
        nation = self._get_nation_by_slug(slug)
        if nation is None:
            raise NationNotFoundError("nation was not found")
        existing_request = self.session.execute(
            select(NationJoinRequest).where(
                NationJoinRequest.nation_id == nation.id,
                NationJoinRequest.user_id == current_user.id,
                NationJoinRequest.status == "pending",
            )
        ).scalar_one_or_none()
        if existing_request is not None:
            raise NationConflictError("join request already exists")
        if nation.recruitment_policy == "invite_only":
            raise NationValidationError("this nation is invite only")
        if nation.recruitment_policy == "open":
            self.session.add(NationMember(nation_id=nation.id, user_id=current_user.id, role="member"))
            self.session.commit()
            return NationJoinActionResponse(message="You joined the nation.", nation=self.get_by_slug(slug, viewer=current_user))
        self.session.add(NationJoinRequest(
            nation_id=nation.id,
            user_id=current_user.id,
            message=(payload.message or "").strip() or None,
            status="pending",
        ))
        self.session.commit()
        return NationJoinActionResponse(message="Join request sent successfully.", nation=self.get_by_slug(slug, viewer=current_user))

    def approve_request(self, current_user: User, slug: str, request_id) -> NationRead:
        nation = self._require_manageable_nation(current_user, slug=slug)
        join_request = self.session.get(NationJoinRequest, request_id)
        if join_request is None or join_request.nation_id != nation.id:
            raise NationNotFoundError("join request was not found")
        if self._find_nation_for_user(join_request.user_id) is not None:
            raise NationConflictError("user is already in a nation")
        join_request.status = "approved"
        self.session.add(NationMember(nation_id=nation.id, user_id=join_request.user_id, role="member"))
        self.session.commit()
        return self.get_by_slug(slug, viewer=current_user)

    def reject_request(self, current_user: User, slug: str, request_id) -> NationRead:
        nation = self._require_manageable_nation(current_user, slug=slug)
        join_request = self.session.get(NationJoinRequest, request_id)
        if join_request is None or join_request.nation_id != nation.id:
            raise NationNotFoundError("join request was not found")
        join_request.status = "rejected"
        self.session.commit()
        return self.get_by_slug(slug, viewer=current_user)

    def update_member_role(
        self,
        *,
        current_user: User,
        slug: str,
        target_user_id: UUID,
        payload: NationMemberRoleUpdateRequest,
    ) -> NationActionResponse:
        nation = self._require_manageable_nation(current_user, slug=slug)
        actor_membership = self._get_membership(nation.id, current_user.id)
        target_membership = self._get_membership(nation.id, target_user_id)

        if target_membership is None:
            raise NationNotFoundError("nation member was not found")

        if target_membership.role == "leader":
            raise NationValidationError("leader role cannot be changed here")

        if actor_membership is None:
            raise NationPermissionError("not enough permissions to manage nation")

        if actor_membership.role == "officer" and target_membership.role == "officer":
            raise NationPermissionError("officer cannot change another officer role")

        target_membership.role = payload.role
        self.session.commit()

        return NationActionResponse(
            message="Member role updated successfully.",
            nation=self.get_by_slug(slug, viewer=current_user),
        )

    def remove_member(
        self,
        *,
        current_user: User,
        slug: str,
        target_user_id: UUID,
    ) -> NationActionResponse:
        nation = self._require_manageable_nation(current_user, slug=slug)
        actor_membership = self._get_membership(nation.id, current_user.id)
        target_membership = self._get_membership(nation.id, target_user_id)

        if target_membership is None:
            raise NationNotFoundError("nation member was not found")

        if target_membership.role == "leader":
            raise NationValidationError("leader cannot be removed from nation")

        if actor_membership is None:
            raise NationPermissionError("not enough permissions to manage nation")

        if actor_membership.role == "officer" and target_membership.role == "officer":
            raise NationPermissionError("officer cannot remove another officer")

        self.session.delete(target_membership)
        self.session.commit()

        return NationActionResponse(
            message="Member removed successfully.",
            nation=self.get_by_slug(slug, viewer=current_user),
        )

    def transfer_leadership(
        self,
        *,
        current_user: User,
        slug: str,
        payload: NationTransferLeadershipRequest,
    ) -> NationActionResponse:
        nation = self._require_manageable_nation(current_user, slug=slug)
        actor_membership = self._get_membership(nation.id, current_user.id)
        if actor_membership is None or actor_membership.role != "leader":
            raise NationPermissionError("only leader can transfer leadership")

        target_membership = self._get_membership(nation.id, payload.target_user_id)
        if target_membership is None:
            raise NationNotFoundError("nation member was not found")
        if target_membership.user_id == current_user.id:
            raise NationValidationError("leadership is already assigned to this user")

        actor_membership.role = "officer"
        target_membership.role = "leader"
        nation.leader_user_id = target_membership.user_id

        self.session.commit()

        return NationActionResponse(
            message="Leadership transferred successfully.",
            nation=self.get_by_slug(slug, viewer=current_user),
        )

    def _slug_exists(self, slug: str) -> bool:
        return self.session.execute(select(Nation).where(Nation.slug == slug)).scalar_one_or_none() is not None

    def _normalize_slug(self, value: str) -> str:
        slug = SLUG_CLEANUP_PATTERN.sub("-", value.strip().lower()).strip("-._")
        if len(slug) < 3:
            raise NationValidationError("nation slug is too short")
        return slug[:64]

    def _get_nation_by_slug(self, slug: str) -> Nation | None:
        return (
            self.session.execute(
                select(Nation)
                .options(
                    joinedload(Nation.members).joinedload(NationMember.user).joinedload(User.player_account),
                    joinedload(Nation.join_requests).joinedload(NationJoinRequest.user).joinedload(User.player_account),
                )
                .where(Nation.slug == slug)
            )
            .unique()
            .scalar_one_or_none()
        )

    def _find_nation_for_user(self, user_id) -> Nation | None:
        return (
            self.session.execute(
                select(Nation)
                .join(NationMember, NationMember.nation_id == Nation.id)
                .options(
                    joinedload(Nation.members).joinedload(NationMember.user).joinedload(User.player_account),
                    joinedload(Nation.join_requests).joinedload(NationJoinRequest.user).joinedload(User.player_account),
                )
                .where(NationMember.user_id == user_id)
            )
            .unique()
            .scalar_one_or_none()
        )

    def _get_membership(self, nation_id, user_id) -> NationMember | None:
        return self.session.execute(
            select(NationMember).where(NationMember.nation_id == nation_id, NationMember.user_id == user_id)
        ).scalar_one_or_none()

    def _require_manageable_nation(self, current_user: User, slug: str | None = None) -> Nation:
        nation = self._get_nation_by_slug(slug) if slug else self._find_nation_for_user(current_user.id)
        if nation is None:
            raise NationNotFoundError("nation was not found")
        membership = next((item for item in nation.members if item.user_id == current_user.id), None)
        if membership is None or membership.role not in {"leader", "officer"}:
            raise NationPermissionError("not enough permissions to manage nation")
        return nation

    def _can_manage(self, nation: Nation, viewer: User | None) -> bool:
        if viewer is None:
            return False
        membership = next((item for item in nation.members if item.user_id == viewer.id), None)
        return membership is not None and membership.role in {"leader", "officer"}

    def _build_read(self, nation: Nation, viewer: User | None = None) -> NationRead:
    viewer_membership = next(
        (item for item in nation.members if viewer is not None and item.user_id == viewer.id),
        None,
    )
    viewer_request = next(
        (
            item
            for item in nation.join_requests
            if viewer is not None and item.user_id == viewer.id and item.status == "pending"
        ),
        None,
    )

    members = [
        NationMemberRead(
            user_id=item.user_id,
            site_login=item.user.site_login if item.user else "unknown",
            minecraft_nickname=item.user.player_account.minecraft_nickname
            if item.user and item.user.player_account
            else None,
            role=item.role,
            created_at=item.created_at,
        )
        for item in sorted(
            nation.members,
            key=lambda x: (x.role != "leader", x.role != "officer", x.created_at),
        )
    ]

    join_requests = []
    if viewer_membership is not None and viewer_membership.role in {"leader", "officer"}:
        join_requests = [
            NationJoinRequestRead(
                id=item.id,
                user_id=item.user_id,
                site_login=item.user.site_login if item.user else "unknown",
                minecraft_nickname=item.user.player_account.minecraft_nickname
                if item.user and item.user.player_account
                else None,
                message=item.message,
                status=item.status,
                created_at=item.created_at,
            )
            for item in nation.join_requests
            if item.status == "pending"
        ]

    version = ""
    if nation.updated_at is not None:
        version = str(int(nation.updated_at.timestamp()))

    def versioned(url: str | None) -> str | None:
        if not url:
            return None
        if not version:
            return url
        separator = "&" if "?" in url else "?"
        return f"{url}{separator}v={version}"

    return NationRead(
        id=nation.id,
        slug=nation.slug,
        title=nation.title,
        tag=nation.tag,
        short_description=nation.short_description,
        description=nation.description,
        accent_color=nation.accent_color,
        recruitment_policy=nation.recruitment_policy,
        is_public=nation.is_public,
        leader_user_id=nation.leader_user_id,
        assets=NationAssetsRead(
            icon_url=versioned(nation.icon_url),
            icon_preview_url=versioned(nation.icon_preview_url),
            banner_url=versioned(nation.banner_url),
            banner_preview_url=versioned(nation.banner_preview_url),
            background_url=versioned(nation.background_url),
            background_preview_url=versioned(nation.background_preview_url),
        ),
        stats=NationStatsRead(
            members_count=len(nation.members),
            pending_requests_count=len([i for i in nation.join_requests if i.status == "pending"]),
        ),
        viewer_role=viewer_membership.role if viewer_membership else None,
        viewer_is_member=viewer_membership is not None,
        viewer_can_manage=viewer_membership is not None and viewer_membership.role in {"leader", "officer"},
        viewer_request_status=viewer_request.status if viewer_request is not None else None,
        members=members,
        join_requests=join_requests,
        created_at=nation.created_at,
        updated_at=nation.updated_at,
    )

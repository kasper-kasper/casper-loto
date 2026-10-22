"""Authenticated manual publications; adapters contain no event rules."""

from datetime import UTC, datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.api.dependencies import (
    CurrentMiniAppUser,
    get_current_miniapp_user,
    get_db_session,
)
from k_loto.api.routes.admin import CurrentAdmin, get_current_admin, require_admin_csrf
from k_loto.application.publication_events import (
    EVENTS,
    EventDraftInput,
    PublicationEventService,
    event_config,
)
from k_loto.application.publications import (
    EditPublicationInput,
    PublicationConflict,
    PublicationInput,
    PublicationService,
    PublicationView,
    RevisionInput,
    template_catalog,
)
from k_loto.core.config import Settings, get_settings
from k_loto.infrastructure.database.models import Publication
from k_loto.infrastructure.publication_channel import channel_status


def require_editorial_enabled() -> None:
    if not get_settings().editorial_enabled:
        raise HTTPException(410, "Editorial publications have been retired.")


router = APIRouter(
    tags=["publications"], dependencies=[Depends(require_editorial_enabled)]
)
Session = Annotated[AsyncSession, Depends(get_db_session)]
Admin = Annotated[CurrentAdmin, Depends(get_current_admin)]
Editor = Annotated[CurrentAdmin, Depends(require_admin_csrf)]


@router.get("/api/v1/admin/publications/event-types")
async def event_types(_admin: Admin) -> dict[str, Any]:
    config = event_config()
    return {
        "types": [vars(item) for item in EVENTS.values()],
        "config": config.model_dump(),
    }


@router.get("/api/v1/admin/publications/events", response_model=list[PublicationView])
async def content_events(
    _admin: Admin,
    session: Session,
    before: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
) -> list[Publication]:
    try:
        return await PublicationService(session).list(
            events=True, before=before, limit=limit
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/api/v1/admin/publications/events/scan")
async def scan_events(admin: Editor, session: Session) -> dict[str, Any]:
    return await PublicationEventService(session).scan(
        now=datetime.now(UTC), force=True, author=admin.user_id
    )


@router.put(
    "/api/v1/admin/publications/events/{publication_id}", response_model=PublicationView
)
async def create_content_draft(
    publication_id: UUID, payload: EventDraftInput, admin: Editor, session: Session
) -> Publication:
    try:
        return await PublicationEventService(session).create_draft(
            payload,
            publication_id=publication_id,
            author=admin.user_id,
            now=datetime.now(UTC),
        )
    except PublicationConflict as exc:
        raise HTTPException(409, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/api/v1/admin/publications/channel")
async def publication_channel(
    _admin: Admin,
    settings: Annotated[Settings, Depends(get_settings)],
    check: bool = False,
) -> dict[str, Any]:
    return await channel_status(settings, check=check)


@router.get("/api/v1/admin/publications/templates")
async def templates(_admin: Admin) -> list[dict[str, Any]]:
    return template_catalog()


@router.get("/api/v1/admin/publications", response_model=list[PublicationView])
async def admin_publications(
    _admin: Admin,
    session: Session,
    before: UUID | None = None,
    view: Literal["all", "suggestions"] = "all",
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
) -> list[Publication]:
    try:
        return await PublicationService(session).list(
            before=before, limit=limit, view=view
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/api/v1/admin/publications/suggestions/prepare")
async def prepare_suggestions(admin: Editor, session: Session) -> dict[str, bool]:
    from k_loto.application.publication_automation import PublicationAutomation

    await PublicationAutomation(session).prepare_suggestions(
        author=admin.user_id, now=datetime.now(UTC)
    )
    return {"prepared": True}


@router.get("/api/v1/miniapp/publications", response_model=list[PublicationView])
async def player_publications(
    _user: Annotated[CurrentMiniAppUser, Depends(get_current_miniapp_user)],
    session: Session,
    before: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
) -> list[Publication]:
    try:
        return await PublicationService(session).list(
            player=True, before=before, limit=limit
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.put(
    "/api/v1/admin/publications/{publication_id}", response_model=PublicationView
)
async def save_publication(
    publication_id: UUID, payload: PublicationInput, admin: Editor, session: Session
) -> Publication:
    try:
        return await PublicationService(session).create(
            payload, author=admin.user_id, publication_id=publication_id
        )
    except PublicationConflict as exc:
        raise HTTPException(409, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.patch(
    "/api/v1/admin/publications/{publication_id}", response_model=PublicationView
)
async def edit_publication(
    publication_id: UUID, payload: EditPublicationInput, admin: Editor, session: Session
) -> Publication:
    try:
        return await PublicationService(session).change(
            publication_id,
            author=admin.user_id,
            revision=payload.revision,
            action="edit",
            payload=payload,
        )
    except PublicationConflict as exc:
        raise HTTPException(409, str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post(
    "/api/v1/admin/publications/{publication_id}/publish",
    response_model=PublicationView,
)
async def publish(
    publication_id: UUID, payload: RevisionInput, admin: Editor, session: Session
) -> Publication:
    return await _transition(publication_id, payload, admin, session, "publish")


@router.post(
    "/api/v1/admin/publications/{publication_id}/archive",
    response_model=PublicationView,
)
async def archive(
    publication_id: UUID, payload: RevisionInput, admin: Editor, session: Session
) -> Publication:
    return await _transition(publication_id, payload, admin, session, "archive")


@router.post(
    "/api/v1/admin/publications/{publication_id}/delete", response_model=PublicationView
)
async def delete_proposal(
    publication_id: UUID, payload: RevisionInput, admin: Editor, session: Session
) -> Publication:
    return await _transition(publication_id, payload, admin, session, "delete")


async def _transition(
    publication_id: UUID,
    payload: RevisionInput,
    admin: CurrentAdmin,
    session: AsyncSession,
    action: Literal["publish", "archive", "delete"],
) -> Publication:
    try:
        return await PublicationService(session).change(
            publication_id,
            author=admin.user_id,
            revision=payload.revision,
            action=action,
        )
    except PublicationConflict as exc:
        raise HTTPException(409, str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc

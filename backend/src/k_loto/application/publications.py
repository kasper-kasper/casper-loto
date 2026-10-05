"""Manual editorial workflow. No detection, scheduling or Telegram delivery."""

import json
from copy import deepcopy
from datetime import UTC, datetime
from functools import lru_cache
from importlib.resources import files
from typing import Any, Literal, cast
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.domain.enums import AuditAction
from k_loto.infrastructure.database.models import AdminAuditLog, Lottery, Publication


class PublicationFields(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kicker: str = Field(default="", max_length=50)
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=240)
    value: str = Field(default="", max_length=80)
    fact: str = Field(default="", max_length=100)

    @model_validator(mode="after")
    def meaningful_title(self) -> "PublicationFields":
        if not self.title.strip():
            raise ValueError("Publication title cannot be blank.")
        return self


class PublicationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    template_id: str = Field(min_length=1, max_length=100)
    fields: PublicationFields
    cta_label: str = Field(default="Открыть лотерею", min_length=1, max_length=40)
    channel_caption: str = Field(default="", max_length=1000)


class PublicationView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    lottery_code: str
    status: Literal["draft", "published", "archived"]
    revision: int
    content: dict[str, Any]
    published_at: datetime | None
    event_type: str | None = None
    event_key: str | None = None
    event_mode: str | None = None
    created_at: datetime
    updated_at: datetime


class RevisionInput(BaseModel):
    revision: int = Field(ge=1)


class EditPublicationInput(PublicationInput):
    revision: int = Field(ge=1)


@lru_cache(maxsize=1)
def template_catalog() -> list[dict[str, Any]]:
    return cast(
        list[dict[str, Any]],
        json.loads(
            files("k_loto.application")
            .joinpath("publication_templates.json")
            .read_text(encoding="utf-8")
        ),
    )


def content_snapshot(payload: PublicationInput) -> dict[str, Any]:
    template = next(
        (item for item in template_catalog() if item["id"] == payload.template_id), None
    )
    if template is None:
        raise ValueError("Unknown publication template.")
    if not payload.cta_label.strip():
        raise ValueError("CTA label cannot be blank.")
    return {
        "template": deepcopy(template),
        "fields": payload.fields.model_dump(),
        "cta_label": payload.cta_label.strip(),
        "channel_caption": payload.channel_caption,
    }


class PublicationConflict(ValueError):
    """A stale revision or attempted edit of a published snapshot."""


class PublicationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(
        self,
        *,
        player: bool = False,
        before: UUID | None = None,
        limit: int = 30,
        events: bool = False,
    ) -> list[Publication]:
        if not 1 <= limit <= 100:
            raise ValueError("Invalid publication page size.")
        if player and events:
            raise ValueError("Nonvisual events are not player publications.")
        statement = select(Publication).where(
            Publication.event_type.is_not(None)
            if events
            else Publication.event_type.is_(None)
        )
        if player:
            statement = statement.where(Publication.status == "published")
        date_column = Publication.published_at if player else Publication.created_at
        # Persisted publication date + UUID gives a stable feed cursor.
        if before is not None:
            cursor = await self.session.get(Publication, before)
            if (
                cursor is None
                or bool(cursor.event_type) != events
                or (player and cursor.status != "published")
            ):
                raise ValueError("Publication cursor does not exist.")
            cursor_date = cursor.published_at if player else cursor.created_at
            statement = statement.where(
                (date_column < cursor_date)
                | ((date_column == cursor_date) & (Publication.id < cursor.id))
            )
        rows = await self.session.scalars(
            statement.order_by(date_column.desc(), Publication.id.desc()).limit(limit)
        )
        return list(rows)

    async def create(
        self, payload: PublicationInput, *, author: UUID, publication_id: UUID
    ) -> Publication:
        snapshot = content_snapshot(payload)
        async with self.session.begin():
            # Serialize retries for a client-generated UUID, avoiding duplicate drafts.
            from sqlalchemy import func

            await self.session.execute(
                select(func.pg_advisory_xact_lock(publication_id.int % (2**63 - 1)))
            )
            existing = await self.session.get(Publication, publication_id)
            if existing is not None:
                if existing.author_id != author or existing.content != snapshot:
                    raise PublicationConflict("Publication identifier already used.")
                return existing
            lottery = await self.session.scalar(
                select(Lottery.code).where(
                    Lottery.code == snapshot["template"]["lottery"]
                )
            )
            if lottery is None and snapshot["template"]["lottery"] not in (
                "kasper-live",
                "casper-loto",
            ):
                raise ValueError("Lottery does not exist.")
            now = datetime.now(UTC)
            row = Publication(
                id=publication_id,
                author_id=author,
                lottery_code=snapshot["template"]["lottery"],
                status="draft",
                revision=1,
                content=snapshot,
                created_at=now,
                updated_at=now,
            )
            self.session.add(row)
            self._audit(row, author, "create", None)
            await self.session.flush()
        return row

    async def change(
        self,
        publication_id: UUID,
        *,
        author: UUID,
        revision: int,
        action: Literal["edit", "publish", "archive"],
        payload: PublicationInput | None = None,
    ) -> Publication:
        snapshot = content_snapshot(payload) if payload is not None else None
        async with self.session.begin():
            row = await self.session.get(
                Publication, publication_id, with_for_update=True
            )
            if row is None:
                raise LookupError("Publication does not exist.")
            if row.event_type is not None and action in ("edit", "publish"):
                raise PublicationConflict(
                    "Nonvisual events require a future content/visual adapter; "
                    "publication is disabled."
                )
            # Exact retry of a successful state transition is harmless.
            target = {"publish": "published", "archive": "archived"}.get(action)
            if target and row.status == target and row.revision == revision + 1:
                return row
            if row.revision != revision:
                raise PublicationConflict("Publication changed; reload it.")
            old = {
                "status": row.status,
                "revision": row.revision,
                "content": deepcopy(row.content),
            }
            if action == "edit":
                if row.status != "draft" or snapshot is None:
                    raise PublicationConflict(
                        "Only drafts can be edited; duplicate a published story first."
                    )
                row.content = snapshot
                row.lottery_code = snapshot["template"]["lottery"]
            elif action == "publish":
                if row.status != "draft":
                    raise PublicationConflict("Only drafts can be published.")
                row.status = "published"
                row.published_at = datetime.now(UTC)
            else:
                row.status = "archived"
            row.revision += 1
            row.updated_at = datetime.now(UTC)
            self._audit(row, author, action, old)
            await self.session.flush()
        return row

    def _audit(
        self, row: Publication, author: UUID, action: str, old: dict[str, Any] | None
    ) -> None:
        self.session.add(
            AdminAuditLog(
                id=uuid4(),
                admin_user_id=author,
                action=AuditAction.CREATE if action == "create" else AuditAction.UPDATE,
                entity_type="PUBLICATION",
                entity_id=row.id,
                old_values=old,
                new_values={
                    "status": row.status,
                    "revision": row.revision,
                    "content": deepcopy(row.content),
                },
                reason=f"Editorial publication: {action}",
            )
        )

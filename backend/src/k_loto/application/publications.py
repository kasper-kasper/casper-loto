"""Manual editorial workflow. No detection, scheduling or Telegram delivery."""

import json
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from importlib.resources import files
from typing import Any, Literal, cast
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import DateTime, func, or_, select
from sqlalchemy import cast as sql_cast
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
def retired_event_types() -> list[str]:
    rules = json.loads(
        files("k_loto.application")
        .joinpath("publication_lottery_config.json")
        .read_text(encoding="utf-8")
    )
    return cast(list[str], rules["retired_event_types"])


@lru_cache(maxsize=1)
def template_catalog() -> list[dict[str, Any]]:
    catalog = cast(
        list[dict[str, Any]],
        json.loads(
            files("k_loto.application")
            .joinpath("publication_templates.json")
            .read_text(encoding="utf-8")
        ),
    )
    return [
        item for item in catalog if item["subcategory"] not in retired_event_types()
    ]


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
        view: Literal["all", "suggestions"] = "all",
    ) -> list[Publication]:
        if not 1 <= limit <= 100:
            raise ValueError("Invalid publication page size.")
        if player and events:
            raise ValueError("Nonvisual events are not player publications.")
        statement = select(Publication).where(
            Publication.event_type.is_not(None)
            if events
            else Publication.content.has_key("template")  # noqa: W601
        )
        statement = statement.where(
            func.coalesce(
                Publication.event_type,
                Publication.content["template"]["subcategory"].astext,
                "",
            ).not_in(retired_event_types())
        )
        statement = statement.where(
            Publication.content["deleted"].as_boolean().is_distinct_from(True)
        )
        if view == "suggestions":
            from k_loto.application.publication_retention import (
                PROPOSAL_LIFETIME,
                pending_proposal_filter,
                proposal_timestamp,
                stale_streak_filter,
            )

            statement = statement.where(
                pending_proposal_filter(),
                proposal_timestamp() > datetime.now(UTC) - PROPOSAL_LIFETIME,
                ~stale_streak_filter(),
            )
        date_column: Any = (
            Publication.published_at if player else Publication.created_at
        )
        if player:
            limit = min(limit, 10)
            cutoff = datetime.now(UTC) - timedelta(hours=24)
            date_column = func.coalesce(
                sql_cast(
                    Publication.content["event"]["occurred_at"].astext,
                    DateTime(timezone=True),
                ),
                Publication.published_at,
            )
            statement = statement.where(
                or_(
                    Publication.status == "published",
                    (Publication.status == "draft")
                    & Publication.content["story_visible"].as_boolean().is_(True),
                ),
                date_column >= cutoff,
            )
        # Persisted publication date + UUID gives a stable feed cursor.
        if before is not None:
            cursor = await self.session.get(Publication, before)
            if (
                cursor is None
                or (events and not cursor.event_type)
                or (not events and "template" not in cursor.content)
                or (
                    player
                    and cursor.status != "published"
                    and not cursor.content.get("story_visible")
                )
            ):
                raise ValueError("Publication cursor does not exist.")
            cursor_date = cursor.published_at if player else cursor.created_at
            if player and cursor.event_type:
                cursor_date = datetime.fromisoformat(
                    cursor.content["event"]["occurred_at"]
                )
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
        action: Literal["edit", "publish", "archive", "delete"],
        payload: PublicationInput | None = None,
    ) -> Publication:
        snapshot = content_snapshot(payload) if payload is not None else None
        async with self.session.begin():
            from k_loto.application.publication_events import PublicationEventService

            await PublicationEventService(self.session)._lock()
            row = await self.session.get(
                Publication, publication_id, with_for_update=True
            )
            if row is None:
                raise LookupError("Publication does not exist.")
            from k_loto.application.publication_retention import (
                proposal_expired,
                stale_streak,
            )

            if action in {"edit", "publish"} and proposal_expired(
                row, datetime.now(UTC)
            ):
                raise PublicationConflict(
                    "Proposal expired after 24 hours; refresh suggestions."
                )
            if action in {"edit", "publish"} and await stale_streak(self.session, row):
                raise PublicationConflict("Jackpot series ended; refresh suggestions.")
            event_code = row.event_type or row.content.get("template", {}).get(
                "subcategory"
            )
            if action in {"edit", "publish"} and event_code in retired_event_types():
                raise PublicationConflict(
                    "Participant-record publications are retired."
                )
            if action == "publish" and row.event_type is not None:
                from k_loto.application.publication_automation import (
                    publication_is_eligible,
                )

                if not publication_is_eligible(
                    row.event_type,
                    row.lottery_code,
                    row.content.get("event", {}).get("payload"),
                ):
                    raise PublicationConflict(
                        "Event does not meet publication eligibility."
                    )
            if (
                row.event_type is not None
                and action in ("edit", "publish")
                and "template" not in row.content
            ):
                raise PublicationConflict(
                    "Nonvisual events require a future content/visual adapter; "
                    "publication is disabled."
                )
            if (
                row.event_type is not None
                and action == "publish"
                and row.status == "draft"
            ):
                delivery = row.content.get("delivery", {})
                if delivery.get("state") == "queued" and row.revision == revision + 1:
                    return row
                if (
                    row.revision != revision
                    or delivery.get("state") != "approval_required"
                ):
                    raise PublicationConflict("Event delivery is already scheduled.")
                old_content = deepcopy(row.content)
                row.content = {
                    **row.content,
                    "delivery": {**delivery, "state": "queued", "manual": True},
                }
                row.revision += 1
                self._audit(row, author, "event_approve", old_content)
                await self.session.flush()
                return row
            # Exact retry of a successful state transition is harmless.
            target = {
                "publish": "published",
                "archive": "archived",
                "delete": "archived",
            }.get(action)
            if (
                target
                and row.status == target
                and row.revision == revision + 1
                and (action != "delete" or row.content.get("deleted"))
            ):
                return row
            if row.revision != revision:
                raise PublicationConflict("Publication changed; reload it.")
            if action in {"edit", "delete"} and row.event_type is not None:
                if (
                    row.status != "draft"
                    or row.content.get("delivery", {}).get("state")
                    != "approval_required"
                ):
                    raise PublicationConflict(
                        "Only proposals awaiting approval can be edited or deleted."
                    )
            if action == "delete" and row.status != "draft":
                raise PublicationConflict("Only unpublished proposals can be deleted.")
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
                if row.event_type is not None:
                    original = row.content
                    if (
                        snapshot["template"]["subcategory"] != row.event_type
                        or snapshot["template"]["lottery"] != row.lottery_code
                        or any(
                            snapshot["fields"][key] != original["fields"][key]
                            for key in ("value", "fact")
                        )
                    ):
                        raise PublicationConflict(
                            "Source event and calculated facts cannot be changed."
                        )
                    from k_loto.application.publication_automation import caption_html

                    caption_html(snapshot["channel_caption"])
                    row.content = {**original, **snapshot}
                else:
                    row.content = snapshot
                row.lottery_code = snapshot["template"]["lottery"]
            elif action == "publish":
                if row.status != "draft":
                    raise PublicationConflict("Only drafts can be published.")
                row.status = "published"
                row.published_at = datetime.now(UTC)
            else:
                delivery = row.content.get("delivery", {})
                attempted_at = delivery.get("attempted_at")
                attempted = (
                    datetime.fromisoformat(attempted_at)
                    if attempted_at
                    else row.updated_at
                )
                if delivery.get("state") == "sending" and attempted > datetime.now(
                    UTC
                ) - timedelta(minutes=5):
                    raise PublicationConflict(
                        "Delivery is in progress; wait for its outcome "
                        "before archiving."
                    )
                row.status = "archived"
                if row.content.get("delivery", {}).get("state") in {
                    "queued",
                    "uncertain",
                    "sending",
                }:
                    row.content = {
                        **row.content,
                        "delivery": {
                            **row.content["delivery"],
                            "previous_state": row.content["delivery"]["state"],
                            "state": "cancelled",
                            "resolved_at": datetime.now(UTC).isoformat(),
                        },
                    }
                if action == "delete":
                    row.content = {
                        **row.content,
                        "deleted": True,
                        "story_visible": False,
                        "delivery": {
                            **row.content.get("delivery", {}),
                            "state": "cancelled",
                        },
                    }
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

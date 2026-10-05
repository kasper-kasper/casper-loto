"""Editorial snapshots, retry safety, locks and authenticated feed boundaries."""

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.application.publications import (
    PublicationConflict,
    PublicationFields,
    PublicationInput,
    PublicationService,
    content_snapshot,
    template_catalog,
)
from k_loto.infrastructure.database.models import AdminAuditLog, Publication
from k_loto.main import create_app


def payload() -> PublicationInput:
    return PublicationInput(
        template_id=template_catalog()[0]["id"],
        fields=PublicationFields(title="Редакторский заголовок", value="42 CAS"),
    )


def stored(status: str = "draft", revision: int = 1) -> Publication:
    now = datetime(2026, 10, 5, tzinfo=UTC)
    return Publication(
        id=UUID(int=1),
        author_id=UUID(int=2),
        lottery_code="pulse",
        status=status,
        revision=revision,
        content=content_snapshot(payload()),
        created_at=now,
        updated_at=now,
        published_at=now if status == "published" else None,
    )


class Transaction:
    async def __aenter__(self) -> None:
        return None

    async def __aexit__(self, *_args: Any) -> None:
        return None


class Session:
    def __init__(
        self, row: Publication | None = None, rows: list[Publication] | None = None
    ) -> None:
        self.row = row
        self.rows = rows or []
        self.added: list[Any] = []
        self.sql: list[str] = []
        self.locked = False

    def begin(self) -> Transaction:
        return Transaction()

    async def get(self, _model: Any, _id: UUID, **kwargs: Any) -> Publication | None:
        self.locked = kwargs.get("with_for_update", False)
        return self.row

    def record(self, statement: Any) -> None:
        self.sql.append(
            str(
                statement.compile(
                    dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
                )
            )
        )

    async def execute(self, statement: Any) -> None:
        self.record(statement)

    async def scalar(self, statement: Any) -> str:
        self.record(statement)
        return "pulse"

    async def scalars(self, statement: Any) -> list[Publication]:
        self.record(statement)
        return self.rows

    def add(self, row: Any) -> None:
        self.added.append(row)

    async def flush(self) -> None:
        pass


def service(session: Session) -> PublicationService:
    return PublicationService(cast(AsyncSession, session))


def test_catalog_and_snapshot_trust_only_server_templates() -> None:
    assert len(template_catalog()) == 2130
    assert all(t["lottery"] != "kasper-live" for t in template_catalog())
    for code in ("weekly", "pll", "pss", "grob"):
        scenes = [
            t
            for t in template_catalog()
            if t["lottery"] == code and t["id"].startswith("atmospheric-v1-")
        ]
        assert len(scenes) == 2 * 32
        assert len({t["formats"]["story"]["background"] for t in scenes}) == 2
        assert len({t["formats"]["post"]["background"] for t in scenes}) == 2
        assert len([t for t in template_catalog() if t["lottery"] == code]) == 130
    with pytest.raises(ValueError):
        content_snapshot(
            payload().model_copy(update={"template_id": "a-live-a3-1-hero"})
        )
    additions = [t for t in template_catalog() if t["id"].startswith("khan-owner-v1-")]
    assert len(additions) == 9 * 32
    assert {t["lottery"] for t in additions} == {"khan"}
    assert len({t["formats"]["story"]["background"] for t in additions}) == 9
    assert len({t["formats"]["post"]["background"] for t in additions}) == 9
    bingo = [t for t in template_catalog() if t["lottery"] == "bingo"]
    assert len(bingo) == 10 * 32
    assert all(t["id"].startswith("bingo-owner-v1-") for t in bingo)
    assert len({t["formats"]["story"]["background"] for t in bingo}) == 10
    assert len({t["formats"]["post"]["background"] for t in bingo}) == 10
    for event in ("A1.1", "A1.5"):
        assert len([t for t in bingo if t["subcategory"] == event]) == 10
    fast = [t for t in template_catalog() if t["id"].startswith("fast-owner-v1-")]
    assert len(fast) == 6 * 32
    for game, art_prefix in (
        ("shadow", "code"),
        ("flash", "flash"),
        ("pulse", "pulse"),
    ):
        assigned = [t for t in fast if t["lottery"] == game]
        assert len(assigned) == 2 * 32
        assert all(t["id"].startswith(f"fast-owner-v1-{art_prefix}-") for t in assigned)
        assert len({t["formats"]["story"]["background"] for t in assigned}) == 2
        assert len({t["formats"]["post"]["background"] for t in assigned}) == 2
    dual = [t for t in template_catalog() if t["lottery"] == "dual"]
    assert len(dual) == 5 * 32
    assert all(t["id"].startswith("dual-owner-v1-") for t in dual)
    assert len({t["formats"]["story"]["background"] for t in dual}) == 5
    assert len({t["formats"]["post"]["background"] for t in dual}) == 5
    snapshot = content_snapshot(payload())
    snapshot["template"]["lottery"] = "hacked"
    assert template_catalog()[0]["lottery"] == "pulse"
    with pytest.raises(ValueError):
        content_snapshot(payload().model_copy(update={"template_id": "../../evil.svg"}))
    with pytest.raises(ValidationError):
        PublicationInput.model_validate(
            {"template_id": "a", "fields": {"title": "x"}, "lottery_code": "other"}
        )
    with pytest.raises(ValidationError):
        PublicationFields(title="   ")
    with pytest.raises(ValidationError):
        PublicationFields(title="x" * 121)


async def test_create_retries_are_serialized_and_audited_once() -> None:
    session = Session()
    row = await service(session).create(
        payload(), author=UUID(int=2), publication_id=UUID(int=1)
    )
    assert row.status == "draft" and row.published_at is None
    assert "pg_advisory_xact_lock" in session.sql[0]
    assert len([item for item in session.added if isinstance(item, AdminAuditLog)]) == 1
    session.row = row
    assert (
        await service(session).create(
            payload(), author=UUID(int=2), publication_id=UUID(int=1)
        )
        is row
    )
    assert len(session.added) == 2
    with pytest.raises(PublicationConflict):
        await service(session).create(
            payload(), author=UUID(int=3), publication_id=UUID(int=1)
        )


async def test_publish_and_archive_are_locked_idempotent_transitions() -> None:
    row = stored()
    session = Session(row)
    original = deepcopy(row.content)
    await service(session).change(
        row.id, author=row.author_id, revision=1, action="publish"
    )
    assert session.locked and row.status == "published" and row.revision == 2
    assert row.published_at is not None and row.published_at.tzinfo == UTC
    await service(session).change(
        row.id, author=row.author_id, revision=1, action="publish"
    )
    assert len(session.added) == 1
    await service(session).change(
        row.id, author=row.author_id, revision=2, action="archive"
    )
    assert row.status == "archived" and row.content == original and row.revision == 3
    await service(session).change(
        row.id, author=row.author_id, revision=2, action="archive"
    )
    assert len(session.added) == 2


@pytest.mark.parametrize("status", ["published", "archived"])
async def test_completed_content_cannot_be_edited_or_republished(status: str) -> None:
    row = stored(status)
    session = Session(row)
    original = deepcopy(row.content)
    with pytest.raises(PublicationConflict):
        await service(session).change(
            row.id, author=row.author_id, revision=1, action="edit", payload=payload()
        )
    with pytest.raises(PublicationConflict):
        await service(session).change(
            row.id, author=row.author_id, revision=1, action="publish"
        )
    assert row.content == original and not session.added


async def test_stale_editor_cannot_overwrite_and_unknown_row_is_missing() -> None:
    row = stored(revision=2)
    with pytest.raises(PublicationConflict):
        await service(Session(row)).change(
            row.id, author=row.author_id, revision=1, action="edit", payload=payload()
        )
    with pytest.raises(LookupError):
        await service(Session()).change(
            UUID(int=1), author=UUID(int=2), revision=1, action="publish"
        )


async def test_player_feed_is_bounded_published_only_and_cursor_is_stable() -> None:
    session = Session(stored("published"))
    await service(session).list(player=True, before=UUID(int=1), limit=30)
    sql = session.sql[0]
    assert "publications.status = 'published'" in sql and "LIMIT 30" in sql
    assert "publications.id <" in sql and "DESC" in sql
    with pytest.raises(ValueError):
        await service(Session(stored("draft"))).list(player=True, before=UUID(int=1))
    with pytest.raises(ValueError):
        await service(session).list(limit=101)


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/admin/publications",
        "/api/v1/admin/publications/templates",
        "/api/v1/miniapp/publications",
    ],
)
def test_publication_reads_require_existing_authentication(path: str) -> None:
    response = TestClient(create_app()).get(path)
    assert response.status_code == 401


def test_editor_requires_csrf_even_with_valid_admin_dependency() -> None:
    from k_loto.api.routes.admin import CurrentAdmin, get_current_admin
    from k_loto.infrastructure.admin_auth import AdminSession

    app = create_app()
    session = AdminSession(
        username="owner", csrf_token="expected", expires_at=9999999999, remembered=False
    )
    app.dependency_overrides[get_current_admin] = lambda: CurrentAdmin(
        UUID(int=2), session
    )
    response = TestClient(app).post(
        "/api/v1/admin/publications/00000000-0000-0000-0000-000000000001/publish",
        json={"revision": 1},
    )
    assert response.status_code == 403

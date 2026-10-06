"""Necessary release check on a disposable production clone; NO Telegram Bot."""

import asyncio
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import func, select

from k_loto.application.publication_automation import (
    PublicationAutomation,
    caption_html,
    deliver_one,
)
from k_loto.application.publication_events import PublicationEventService
from k_loto.application.publication_render import render_post
from k_loto.infrastructure.database.models import Publication
from k_loto.infrastructure.database.session import engine, session_factory


class FakeTransport:
    calls = 0
    fail = False

    async def send_photo(self, *args, **kwargs):
        self.calls += 1
        if self.fail:
            raise TimeoutError("unknown delivery outcome")
        assert kwargs["photo"].data.startswith(b"\x89PNG")
        return SimpleNamespace(message_id=123, chat=SimpleNamespace(id=-123))


async def main() -> None:
    if not str(engine.url.database).endswith("_smoke"):
        raise RuntimeError("Disposable database required")
    end = datetime.now(UTC)
    start = end - timedelta(minutes=30)
    async with session_factory() as session:
        counts = await PublicationAutomation(session).collect(
            start, end, historical=True
        )
    async with session_factory() as session:
        samples = list(
            await session.scalars(
                select(Publication)
                .where(Publication.content["delivery"]["state"].astext == "queued")
                .distinct(Publication.event_type)
                .order_by(Publication.event_type, Publication.created_at)
            )
        )
        assert samples
        for row in samples:
            assert "{" not in row.content["channel_caption"]
            assert "Событие:" in row.content["channel_caption"]
            assert len(row.content["channel_caption"].encode("utf-16-le")) // 2 <= 1024
            assert render_post(
                row.content,
                assets=Path("/app/publication-assets"),
                fonts=Path("/usr/share/fonts/truetype/dejavu"),
            ).startswith(b"\x89PNG")
            assert "[ПОД СПОЙЛЕРОМ:" not in caption_html(row.content["channel_caption"])
        first = samples[0]
        identifier, key = first.id, first.event_key
    # The existing unique key is the deduplication boundary of the shared engine.
    async with session_factory() as session, session.begin():
        service = PublicationEventService(session)
        await service._lock()
        row = await session.get(Publication, identifier)
        duplicate = await service._store(
            key,
            row.event_type,
            row.content["event"]["payload"],
            end,
            row.author_id,
            key,
        )
        assert duplicate.id == identifier
        state = await service._state("publication.transport")
        state.value = {"enabled": True}
    fake = FakeTransport()
    assert await deliver_one(session_factory, fake, now=end) == "sent"
    fake.fail = True
    assert await deliver_one(session_factory, fake, now=end) == "uncertain"
    calls = fake.calls
    assert await deliver_one(session_factory, fake, now=end) == "uncertain"
    assert fake.calls == calls
    async with session_factory() as session:
        sent = await session.scalar(
            select(func.count())
            .select_from(Publication)
            .where(Publication.content["delivery"]["state"].astext == "sent")
        )
        assert sent == 1
    print(
        json.dumps(
            {
                "queue": counts,
                "rendered_types": len(samples),
                "fake_sends": calls,
                "deduplication": "OK",
                "uncertain_send_blocks_retry": "OK",
            }
        )
    )
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

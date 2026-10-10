"""Real PostgreSQL regression checks; called only by the guarded clone script."""

from copy import deepcopy
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import func, select, text

from k_loto.application.distribution import recover_results
from k_loto.application.jackpot_cycles import last_cycle_ends
from k_loto.application.publication_retention import expire_proposals
from k_loto.application.publications import (
    PublicationConflict,
    PublicationFields,
    PublicationInput,
    PublicationService,
    content_snapshot,
    template_catalog,
)
from k_loto.infrastructure.database.models import (
    AdminAuditLog,
    DistributionAnnouncement,
    Publication,
)
from k_loto.infrastructure.database.session import session_factory


async def verify_followup(uid, lid, did, stamp, now):
    from k_loto.core.config import get_settings

    assert (
        str(get_settings().database_url)
        .rstrip("/")
        .endswith("/k_loto_distribution_smoke")
    )
    async with session_factory() as s:
        reset = last_cycle_ends()
        assert (
            await s.scalar(select(reset.c.last_reset).where(reset.c.lottery_id == lid))
            == stamp
        )
        receipts = (
            await s.scalars(
                select(DistributionAnnouncement).where(
                    DistributionAnnouncement.draw_id == did
                )
            )
        ).all()
        assert {r.kind for r in receipts} == {"schedule", "result"}
        assert all(r.state == "sent" for r in receipts)
        result = next(r for r in receipts if r.kind == "result")
        assert "Выигрышных билетов: 3." in result.text
        assert "Все выигрыши уже зачислены." in result.text
    await recover_results(session_factory, now=stamp)
    await recover_results(session_factory, now=stamp)
    async with session_factory() as s:
        assert (
            await s.scalar(
                select(func.count(DistributionAnnouncement.id)).where(
                    DistributionAnnouncement.draw_id == did
                )
            )
            == 2
        )

    snapshot = content_snapshot(
        PublicationInput(
            template_id=next(
                t["id"]
                for t in template_catalog()
                if t["lottery"] == "weekly" and t["subcategory"] == "A5.6"
            ),
            fields=PublicationFields(title="Disposable proposal"),
        )
    )
    expired, fresh, published, stale, current = (uuid4() for _ in range(5))
    own = [expired, fresh, published, stale, current]
    before_draws_query = text(
        "SELECT md5(coalesce(string_agg(row_to_json(t)::text, '' ORDER BY id), '')) "
        "FROM draws t WHERE status='COMPLETED'"
    )
    async with session_factory() as s, s.begin():
        before_draws = await s.scalar(before_draws_query)
        for pid, status, age in [
            (expired, "draft", 25),
            (fresh, "draft", 1),
            (published, "published", 48),
            (stale, "draft", 1),
            (current, "draft", 1),
        ]:
            content = deepcopy(snapshot)
            event = pid in {stale, current}
            if event:
                content.update(
                    delivery={"state": "approval_required"},
                    event={
                        "occurred_at": now.isoformat(),
                        "payload": {
                            "reset_draw_id": str(did) if pid == current else "origin"
                        },
                    },
                )
            s.add(
                Publication(
                    id=pid,
                    author_id=uid,
                    lottery_code="weekly",
                    status=status,
                    revision=1,
                    content=content,
                    event_type="A5.6" if event else None,
                    event_key=f"smoke:{pid}" if event else None,
                    created_at=now - timedelta(hours=age),
                    updated_at=now,
                    published_at=now if status == "published" else None,
                )
            )
    async with session_factory() as s:
        rows = await PublicationService(s).list(view="suggestions", limit=100)
        visible = {r.id for r in rows}
        assert fresh in visible and current in visible
        assert not visible.intersection({expired, published, stale})
    async with session_factory() as s:
        try:
            await PublicationService(s).change(
                expired, author=uid, revision=1, action="publish"
            )
        except PublicationConflict:
            pass
        else:
            raise AssertionError("Expired draft published")
    await expire_proposals(session_factory, now=now)
    assert await expire_proposals(session_factory, now=now) == 0
    async with session_factory() as s:
        rows = {
            r.id: r
            for r in (
                await s.scalars(select(Publication).where(Publication.id.in_(own)))
            ).all()
        }
        assert rows[expired].status == rows[stale].status == "archived"
        assert rows[expired].content["proposal_expiration"]["reason"] == "24_hours"
        assert (
            rows[stale].content["proposal_expiration"]["reason"]
            == "jackpot_cycle_ended"
        )
        assert rows[fresh].status == rows[current].status == "draft"
        assert rows[published].status == "published" and rows[published].revision == 1
        assert (
            await s.scalar(
                select(func.count(AdminAuditLog.id)).where(
                    AdminAuditLog.entity_id.in_([expired, stale])
                )
            )
            == 2
        )
        assert await s.scalar(before_draws_query) == before_draws
    print(
        "Distribution reset SQL, result receipt idempotency, fresh/manual proposals, "
        "24h rejection/archiving, stale epochs, audit and immutable draws PASS"
    )

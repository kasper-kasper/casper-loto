from uuid import uuid4

from k_loto.infrastructure import rate_limit


def test_purchase_rate_limit_reopens_after_five_seconds(monkeypatch) -> None:
    now = 100.0
    monkeypatch.setattr(rate_limit, "monotonic", lambda: now)
    limiter = rate_limit.PurchaseRateLimiter()
    user_id = uuid4()

    assert limiter.allow(user_id, limit=1)
    assert not limiter.allow(user_id, limit=1)

    now = 105.0
    assert limiter.allow(user_id, limit=1)

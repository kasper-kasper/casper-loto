"""The laptop launcher must never inherit production credentials or endpoints."""

import json
import os
import sys

import pytest
from scripts import local_preview


def test_preview_discards_inherited_application_settings(monkeypatch):
    for key in (
        "DATABASE_URL",
        "LOTTERY_BOT_TOKEN",
        "ADMIN_SECRET",
        "WEB_SESSION_SECRET",
        "SERVER_PASSWORD",
        "PUBLICATION_CHANNEL",
        "VITE_API_BASE_URL",
        "APP_ENV",
        "VITE_DESIGN_PREVIEW",
    ):
        monkeypatch.setenv(key, "untrusted-inherited-value")
    env = local_preview.isolated_environment("local-only-secret" * 3)
    assert env["DATABASE_URL"].endswith("@127.0.0.1:55439/k_loto_achievement_preview")
    assert env["APP_ENV"] == "development"
    assert env["VITE_API_BASE_URL"] == ""
    assert env["VITE_DESIGN_PREVIEW"] == "false"
    assert env["EDITORIAL_ENABLED"] == "false"
    assert env["ACHIEVEMENTS_NOTIFICATIONS_ENABLED"] == "false"
    assert not set(env) & {
        "LOTTERY_BOT_TOKEN",
        "ADMIN_SECRET",
        "SERVER_PASSWORD",
        "WEB_SESSION_SECRET",
        "PUBLICATION_CHANNEL",
    }


def test_child_settings_do_not_load_the_repository_env(tmp_path, monkeypatch):
    monkeypatch.setattr(local_preview, "RUNTIME", tmp_path)
    env = local_preview.isolated_environment("local-only-secret" * 3)
    result = local_preview.run(
        [
            sys.executable,
            "-c",
            (
                "import json; from k_loto.core.config import get_settings; "
                "s=get_settings(); print(json.dumps([s.app_env, "
                "s.database_url.hosts()[0]['host'], "
                "s.database_url.path, s.local_dev_auth_available, "
                "s.lottery_bot_token is None, s.admin_secret is None]))"
            ),
        ],
        env=env,
    )
    assert json.loads(result) == [
        "development",
        "127.0.0.1",
        "/k_loto_achievement_preview",
        True,
        True,
        True,
    ]


@pytest.mark.skipif(os.name != "nt", reason="Windows shortcut lock")
def test_second_click_reuses_instance_and_lock_releases(tmp_path, monkeypatch):
    monkeypatch.setattr(local_preview, "RUNTIME", tmp_path)
    first = local_preview.claim_instance()
    assert first is not None
    try:
        assert local_preview.claim_instance() is None
    finally:
        first.close()
    restarted = local_preview.claim_instance()
    assert restarted is not None
    restarted.close()

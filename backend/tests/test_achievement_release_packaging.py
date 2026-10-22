"""Deployment credentials can remain outside the clean release snapshot."""

from scripts.release_vps import load_local_env


def test_release_accepts_environment_only_credentials_without_an_env_copy(tmp_path):
    assert load_local_env(tmp_path / ".env") == {}
    sample = tmp_path / ".env"
    sample.write_text("# local only\nSERVER_USER='test-owner'\n", encoding="utf-8")
    assert load_local_env(sample) == {"SERVER_USER": "test-owner"}

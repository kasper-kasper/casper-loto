"""Production web retirement must preserve the Mini App and Admin routes."""


def test_disabled_web_has_no_routes_but_keeps_miniapp_and_admin(monkeypatch) -> None:
    from k_loto.core.config import Settings
    from k_loto.main import create_app

    settings = Settings(web_enabled=False)
    monkeypatch.setattr("k_loto.main.get_settings", lambda: settings)
    paths = create_app().openapi()["paths"]
    assert not any(path.startswith("/api/v1/web") for path in paths)
    assert any(path.startswith("/api/v1/miniapp") for path in paths)
    assert any(path.startswith("/api/v1/admin") for path in paths)

"""Tests for the soundboard status indicator (green/red dot + tooltip) shown in the
Soundboard tab label on the publicly visible main page."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from chatbot2k.dependencies import get_app_state
from chatbot2k.dependencies import get_common_context
from chatbot2k.routes import commands
from chatbot2k.routes import viewer
from chatbot2k.types.template_contexts import CommonContext


class _FakeDatabase:
    def get_constants(self) -> list[object]:
        return []


class _FakeDictionary:
    def as_dict(self) -> dict[str, str]:
        return {}


def _make_client(*, is_soundboard_enabled: bool) -> TestClient:
    app_state_mock = type(
        "FakeAppState",
        (),
        {
            "command_handlers": [],
            "database": _FakeDatabase(),
            "dictionary": _FakeDictionary(),
            "is_soundboard_enabled": is_soundboard_enabled,
        },
    )()

    app = FastAPI()
    app.include_router(commands.router)
    app.include_router(viewer.router)
    app.dependency_overrides[get_app_state] = lambda: app_state_mock
    app.dependency_overrides[get_common_context] = lambda: CommonContext(
        bot_name="TestBot",
        author_name="Tester",
        copyright_year=2026,
        current_user=None,
        profile_image_url=None,
        is_broadcaster=False,
        pending_clips_count=0,
        unread_notifications_count=0,
        total_notifications_count=0,
    )
    return TestClient(app)


def test_shows_green_dot_and_enabled_tooltip_when_enabled() -> None:
    client = _make_client(is_soundboard_enabled=True)

    response = client.get("/")

    assert response.status_code == 200
    assert 'class="status-dot enabled"' in response.text
    assert "Soundboard is currently" in response.text
    assert "enabled" in response.text.split("Soundboard is currently", 1)[1][:20]


def test_shows_red_dot_and_disabled_tooltip_when_disabled() -> None:
    client = _make_client(is_soundboard_enabled=False)

    response = client.get("/")

    assert response.status_code == 200
    assert 'class="status-dot disabled"' in response.text
    assert "Soundboard is currently" in response.text
    assert "disabled" in response.text.split("Soundboard is currently", 1)[1][:20]

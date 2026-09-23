"""Tests for issue #113: Enable/Disable Soundboard buttons in the admin web
interface. The button's state is kept in sync (including with the
!soundboard enable|disable chat command) via a public SSE stream - see
test_public_soundboard_events.py for that stream itself; these tests cover
just the admin page rendering and the (broadcaster-gated) toggle route."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from chatbot2k.dependencies import get_app_state
from chatbot2k.dependencies import get_broadcaster_user
from chatbot2k.dependencies import get_common_context
from chatbot2k.routes import admin
from chatbot2k.routes import commands
from chatbot2k.routes import viewer
from chatbot2k.types.template_contexts import CommonContext
from chatbot2k.types.user_info import UserInfo


class _FakeDatabase:
    def get_soundboard_commands(self) -> list[object]:
        return []


class _FakeAppState:
    def __init__(self, *, is_soundboard_enabled: bool = True) -> None:
        self.database = _FakeDatabase()
        self.command_handlers: list[object] = []
        self.is_soundboard_enabled = is_soundboard_enabled


def _make_client(app_state: _FakeAppState) -> TestClient:
    app = FastAPI()
    app.include_router(admin.router)
    app.include_router(commands.router)
    app.include_router(viewer.router)
    app.dependency_overrides[get_app_state] = lambda: app_state
    app.dependency_overrides[get_broadcaster_user] = lambda: UserInfo(id="1", login="mod", display_name="Mod")
    app.dependency_overrides[get_common_context] = lambda: CommonContext(
        bot_name="TestBot",
        author_name="Tester",
        copyright_year=2026,
        current_user=UserInfo(id="1", login="mod", display_name="Mod"),
        profile_image_url=None,
        is_broadcaster=True,
        pending_clips_count=0,
        unread_notifications_count=0,
        total_notifications_count=0,
    )
    return TestClient(app)


def test_page_shows_enabled_state_and_button() -> None:
    app_state = _FakeAppState(is_soundboard_enabled=True)
    client = _make_client(app_state)

    response = client.get("/admin/soundboard")

    assert response.status_code == 200
    assert "Disable Soundboard" in response.text
    assert 'class="soundboard-status enabled"' in response.text


def test_page_shows_disabled_state_and_button() -> None:
    app_state = _FakeAppState(is_soundboard_enabled=False)
    client = _make_client(app_state)

    response = client.get("/admin/soundboard")

    assert response.status_code == 200
    assert "Enable Soundboard" in response.text
    assert 'class="soundboard-status disabled"' in response.text


def test_post_disables_the_soundboard() -> None:
    app_state = _FakeAppState(is_soundboard_enabled=True)
    client = _make_client(app_state)

    response = client.post("/admin/soundboard/enabled", json={"is_enabled": False})

    assert response.status_code == 200
    assert app_state.is_soundboard_enabled is False


def test_post_enables_the_soundboard() -> None:
    app_state = _FakeAppState(is_soundboard_enabled=False)
    client = _make_client(app_state)

    response = client.post("/admin/soundboard/enabled", json={"is_enabled": True})

    assert response.status_code == 200
    assert app_state.is_soundboard_enabled is True

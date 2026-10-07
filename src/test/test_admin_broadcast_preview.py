"""Tests for issue #238: showing a render preview (e.g. with constants replaced) below each broadcast
in the admin dashboard, which updates live while editing the message."""

import re
from typing import Final
from typing import NamedTuple

from fastapi import FastAPI
from fastapi.testclient import TestClient

from chatbot2k.broadcasters.utils import render_broadcast_message
from chatbot2k.database.tables import Broadcast
from chatbot2k.database.tables import Constant
from chatbot2k.database.tables import StaticCommand
from chatbot2k.dependencies import get_app_state
from chatbot2k.dependencies import get_broadcaster_user
from chatbot2k.dependencies import get_common_context
from chatbot2k.routes import admin
from chatbot2k.routes import commands as commands_routes
from chatbot2k.routes import viewer
from chatbot2k.types.configuration_setting_kind import ConfigurationSettingKind
from chatbot2k.types.template_contexts import CommonContext
from chatbot2k.types.user_info import UserInfo


class _FakeDatabase:
    def __init__(self, broadcasts: list[Broadcast]) -> None:
        self._broadcasts: Final = broadcasts

    def get_broadcasts(self) -> list[Broadcast]:
        return self._broadcasts

    def get_static_commands(self) -> list[StaticCommand]:
        return []

    def get_constants(self) -> list[Constant]:
        return [
            Constant(name="holy", text="Holy moly!"),
            Constant(name="html", text="<b>bold</b>"),
            Constant(name="markdown", text="**bold** and _italic_"),
            Constant(name="script", text='<script>alert("x")</script>'),
        ]

    def retrieve_configuration_setting_or_default[T](self, kind: ConfigurationSettingKind, default: T) -> T:
        return default


class _FakeAppState(NamedTuple):
    database: _FakeDatabase


def _make_client(broadcasts: list[Broadcast]) -> TestClient:
    app = FastAPI()
    app.include_router(admin.router)
    app.include_router(commands_routes.router)  # For the navbar links.
    app.include_router(viewer.router)  # For the navbar links.
    app.dependency_overrides[get_app_state] = lambda: _FakeAppState(_FakeDatabase(broadcasts))
    app.dependency_overrides[get_broadcaster_user] = lambda: UserInfo(id="1", login="owner", display_name="Owner")
    app.dependency_overrides[get_common_context] = lambda: CommonContext(
        bot_name="TestBot",
        author_name="Tester",
        copyright_year=2026,
        current_user=UserInfo(id="1", login="owner", display_name="Owner"),
        profile_image_url=None,
        is_broadcaster=True,
        pending_clips_count=0,
        unread_notifications_count=0,
        total_notifications_count=0,
    )
    return TestClient(app)


def test_render_broadcast_message_replaces_constants_and_builtins() -> None:
    app_state: Final = _FakeAppState(_FakeDatabase([]))

    rendered: Final = render_broadcast_message(
        "{holy} It is {CURRENT_DATE}. {unknown}",
        app_state,  # type: ignore[reportArgumentType]
    )

    assert rendered.startswith("Holy moly! It is ")
    assert "{CURRENT_DATE}" not in rendered
    # Unknown placeholders are sent as-is, so the preview shows them as-is, too.
    assert rendered.endswith(". {unknown}")


def _extract_previews(html: str, preview_id: str) -> tuple[str, str]:
    """Returns the contents of the raw and the formatted preview with the given ID."""
    match: Final = re.search(
        rf'<div id="{preview_id}" class="broadcast-preview" aria-live="polite">.*?'
        + r'<div class="broadcast-preview-text" data-preview-text>(.*?)</div>.*?'
        + r'<div class="broadcast-preview-html" data-preview-html>(.*?)</div>',
        html,
        re.DOTALL,
    )
    assert match is not None
    return match.group(1), match.group(2)


def test_broadcasts_page_shows_preview_row_below_each_broadcast() -> None:
    client: Final = _make_client(
        [
            Broadcast(id=1, interval_seconds=60, message="{holy}", alias_command=None),
            Broadcast(id=2, interval_seconds=120, message="Look: {markdown}", alias_command=None),
        ]
    )

    response: Final = client.get("/admin/broadcasts")

    assert response.status_code == 200
    preview_rows: Final = re.findall(
        r'<tr class="broadcast-preview-row">\s*<td></td>\s*<td colspan="2">(.*?)</td>\s*<td></td>\s*</tr>',
        response.text,
        re.DOTALL,
    )
    assert len(preview_rows) == 2
    assert 'id="broadcast-preview-1"' in preview_rows[0]
    assert 'id="broadcast-preview-2"' in preview_rows[1]
    assert _extract_previews(response.text, "broadcast-preview-1") == ("Holy moly!", "<p>Holy moly!</p>\n")
    assert _extract_previews(response.text, "broadcast-preview-2") == (
        "Look: **bold** and _italic_",
        "<p>Look: <strong>bold</strong> and <em>italic</em></p>\n",
    )
    # The textareas are hooked up to their previews.
    assert 'data-preview-id="broadcast-preview-1"' in response.text
    assert 'data-preview-id="broadcast-preview-2"' in response.text


def test_broadcasts_page_escapes_raw_preview_and_sanitizes_formatted_preview() -> None:
    client: Final = _make_client(
        [Broadcast(id=1, interval_seconds=60, message="{script}", alias_command=None)],
    )

    response: Final = client.get("/admin/broadcasts")

    assert response.status_code == 200
    raw, formatted = _extract_previews(response.text, "broadcast-preview-1")
    assert raw == "&lt;script&gt;alert(&#34;x&#34;)&lt;/script&gt;"
    assert "<script" not in formatted
    assert "&lt;script" not in formatted


def test_preview_endpoint_renders_unsaved_message() -> None:
    client: Final = _make_client([])

    response: Final = client.post("/admin/broadcasts/preview", json={"message": "{holy} {markdown}"})

    assert response.status_code == 200
    assert response.json() == {
        "text": "Holy moly! **bold** and _italic_",
        "html": "<p>Holy moly! <strong>bold</strong> and <em>italic</em></p>\n",
    }


def test_preview_endpoint_sanitizes_formatted_preview() -> None:
    client: Final = _make_client([])

    response: Final = client.post("/admin/broadcasts/preview", json={"message": "{script}"})

    assert response.status_code == 200
    assert response.json()["text"] == '<script>alert("x")</script>'
    assert "<script" not in response.json()["html"]


def test_preview_endpoint_requires_message() -> None:
    client: Final = _make_client([])

    response: Final = client.post("/admin/broadcasts/preview", json={})

    assert response.status_code == 422


def test_preview_endpoint_requires_broadcaster() -> None:
    client: Final = _make_client([])
    del client.app.dependency_overrides[get_broadcaster_user]  # type: ignore[reportAttributeAccessIssue]

    response: Final = client.post("/admin/broadcasts/preview", json={"message": "{holy}"})

    assert response.status_code == 401


def test_add_broadcast_form_has_empty_preview() -> None:
    client: Final = _make_client([])

    response: Final = client.get("/admin/broadcasts")

    assert response.status_code == 200
    assert (
        'name="message" placeholder="Enter broadcast message..." required data-preview-id="broadcast-preview-add"'
        in (response.text)
    )
    assert _extract_previews(response.text, "broadcast-preview-add") == ("", "")

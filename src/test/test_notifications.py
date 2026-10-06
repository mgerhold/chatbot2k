"""Tests for notifications, whose messages are stored and displayed as HTML (so that they
can contain links) while user-provided values are still escaped."""

from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Optional
from typing import cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel
from starlette.templating import Jinja2Templates

from chatbot2k.app_state import AppState
from chatbot2k.database.tables import Notification
from chatbot2k.dependencies import get_app_state
from chatbot2k.dependencies import get_authenticated_user
from chatbot2k.dependencies import get_common_context
from chatbot2k.dependencies import get_templates
from chatbot2k.routes import commands
from chatbot2k.routes import viewer
from chatbot2k.types.template_contexts import ClipRejectedContext
from chatbot2k.types.template_contexts import CommonContext
from chatbot2k.types.user_info import UserInfo
from chatbot2k.utils.notifications import notify_user


class _FakeDatabase:
    def __init__(self, notifications: Optional[list[Notification]] = None) -> None:
        self.notifications = [] if notifications is None else notifications

    def add_notification(self, *, twitch_user_id: str, message: str, sent_at: datetime) -> None:
        self.notifications.append(
            Notification(twitch_user_id=twitch_user_id, message=message, sent_at=sent_at, has_been_read=False)
        )

    def get_notifications(self, *, twitch_user_id: str) -> list[Notification]:
        return [n for n in self.notifications if n.twitch_user_id == twitch_user_id]

    def get_user_profile(self, *, twitch_user_id: str) -> None:
        # No profile => no email is sent.
        return None


def _make_app_state(database: _FakeDatabase) -> AppState:
    return cast(AppState, type("FakeAppState", (), {"database": database})())


class _EmptyContext(BaseModel):
    pass


@pytest.mark.asyncio
async def test_notification_escapes_user_provided_values() -> None:
    database = _FakeDatabase()

    await notify_user(
        twitch_user_id="123",
        templates=get_templates(),
        notification_template_name="notifications/clip_rejected.html",
        notification_template_context=ClipRejectedContext(
            suggested_command='!<script>alert("x")</script>',
            reason="<a href='https://evil.example'>click</a>",
        ),
        email_template_name="emails/clip_rejected.txt.j2",
        email_subject="Subject",
        email_template_context=_EmptyContext(),
        app_state=_make_app_state(database),
    )

    assert len(database.notifications) == 1
    message = database.notifications[0].message
    assert "<script>" not in message
    assert "&lt;script&gt;" in message
    assert "<a href" not in message
    assert "&lt;a href" in message
    # Markup from the template itself is kept.
    assert "<br>" in message


@pytest.mark.asyncio
async def test_notification_template_without_autoescaping_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "unescaped.txt.j2").write_text("{{ value }}")
    database = _FakeDatabase()

    with pytest.raises(ValueError, match="not autoescaped"):
        await notify_user(
            twitch_user_id="123",
            templates=Jinja2Templates(tmp_path),
            notification_template_name="unescaped.txt.j2",
            notification_template_context=_EmptyContext(),
            email_template_name="unescaped.txt.j2",
            email_subject="Subject",
            email_template_context=_EmptyContext(),
            app_state=_make_app_state(database),
        )

    assert database.notifications == []


def test_notifications_page_renders_message_as_html() -> None:
    database = _FakeDatabase(
        [
            Notification(
                id=1,
                twitch_user_id="123",
                message='Please review <a href="/admin/pending-clips">the clip</a> &amp; more.',
                sent_at=datetime(2026, 1, 1, tzinfo=UTC),
                has_been_read=False,
            )
        ]
    )

    app = FastAPI()
    app.include_router(commands.router)
    app.include_router(viewer.router)
    app.dependency_overrides[get_app_state] = lambda: _make_app_state(database)
    app.dependency_overrides[get_authenticated_user] = lambda: UserInfo(id="123", login="tester", display_name="Tester")
    app.dependency_overrides[get_common_context] = lambda: CommonContext(
        bot_name="TestBot",
        author_name="Tester",
        copyright_year=2026,
        current_user=None,
        profile_image_url=None,
        is_broadcaster=False,
        pending_clips_count=0,
        unread_notifications_count=1,
        total_notifications_count=1,
    )
    client = TestClient(app)

    response = client.get("/viewer/notifications")

    assert response.status_code == 200
    assert 'Please review <a href="/admin/pending-clips">the clip</a> &amp; more.' in response.text

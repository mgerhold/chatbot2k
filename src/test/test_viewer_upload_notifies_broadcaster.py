"""Tests for notifying the broadcaster (in-app and via email) when a user uploads a soundboard clip."""

from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Optional

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from chatbot2k.database.tables import Notification
from chatbot2k.dependencies import get_app_state
from chatbot2k.dependencies import get_authenticated_user
from chatbot2k.routes import admin
from chatbot2k.routes import viewer
from chatbot2k.types.configuration_setting_kind import ConfigurationSettingKind
from chatbot2k.types.template_contexts import NewPendingClipEmailContext
from chatbot2k.types.user_info import UserInfo
from chatbot2k.utils import notifications

_BROADCASTER_ID = "1000"
_UPLOADER = UserInfo(id="2000", login="uploader", display_name="<b>Uploader</b>")


class _FakeDatabase:
    def __init__(self, broadcaster_profile: Optional[object]) -> None:
        self.notifications: list[Notification] = []
        self.pending_clips: list[str] = []
        self._broadcaster_profile = broadcaster_profile

    def retrieve_configuration_setting(self, kind: ConfigurationSettingKind) -> Optional[str]:
        return "10" if kind.name.startswith("MAX_PENDING_SOUNDBOARD_CLIPS") else None

    def retrieve_configuration_setting_or_default[T](self, kind: ConfigurationSettingKind, default: T) -> str | T:
        return default

    def get_number_of_pending_soundboard_clips(self) -> int:
        return len(self.pending_clips)

    def get_pending_soundboard_clips_by_twitch_user_id(self, *, twitch_user_id: str) -> list[object]:
        return []

    def add_pending_soundboard_clip(self, *, name: str, **kwargs: object) -> None:
        self.pending_clips.append(name)

    def add_notification(self, *, twitch_user_id: str, message: str, sent_at: datetime) -> None:
        self.notifications.append(
            Notification(twitch_user_id=twitch_user_id, message=message, sent_at=sent_at, has_been_read=False)
        )

    def get_user_profile(self, *, twitch_user_id: str) -> Optional[object]:
        return self._broadcaster_profile if twitch_user_id == _BROADCASTER_ID else None


def _make_client(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    database: _FakeDatabase,
    *,
    broadcaster_id: Optional[str],
) -> TestClient:
    async def _resolve_broadcaster_id(app_state: object, user_id: str) -> Optional[str]:
        return broadcaster_id

    async def _get_file_extension_by_mime_type(contents: bytes) -> str:
        return ".mp3"

    monkeypatch.setattr(viewer, "resolve_broadcaster_id", _resolve_broadcaster_id)
    monkeypatch.setattr(viewer, "get_file_extension_by_mime_type", _get_file_extension_by_mime_type)
    monkeypatch.setattr(viewer, "SOUNDBOARD_FILES_DIRECTORY", tmp_path)

    app_state = SimpleNamespace(
        database=database,
        config=SimpleNamespace(twitch_channel="the_broadcaster", smtp_settings=object()),
    )

    app = FastAPI()
    app.include_router(viewer.router)
    app.include_router(admin.router)
    app.dependency_overrides[get_app_state] = lambda: app_state
    app.dependency_overrides[get_authenticated_user] = lambda: _UPLOADER
    return TestClient(app, follow_redirects=False)


def _upload(client: TestClient) -> int:
    response = client.post(
        "/viewer/soundboard/upload",
        data={"command_name": "!<i>boom</i>", "agree_terms": "on"},
        files={"file": ("boom.mp3", b"fake audio", "audio/mpeg")},
    )
    return response.status_code


def test_upload_notifies_broadcaster_with_link_to_pending_clips(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    database = _FakeDatabase(broadcaster_profile=None)
    client = _make_client(monkeypatch, tmp_path, database, broadcaster_id=_BROADCASTER_ID)

    assert _upload(client) == 303

    assert database.pending_clips == ["<i>boom</i>"]
    assert len(database.notifications) == 1
    notification = database.notifications[0]
    assert notification.twitch_user_id == _BROADCASTER_ID
    assert '<a href="/admin/pending-clips">' in notification.message
    # User-provided values are escaped.
    assert "&lt;b&gt;Uploader&lt;/b&gt;" in notification.message
    assert "&lt;i&gt;boom&lt;/i&gt;" in notification.message


def test_upload_emails_broadcaster_with_verified_email(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    sent_emails: list[tuple[str, str, Optional[BaseModel]]] = []

    async def _send_email(
        to_address: str,
        subject: str,
        template: object,
        context: Optional[BaseModel],
        settings: object,
    ) -> None:
        sent_emails.append((to_address, subject, context))

    monkeypatch.setattr(notifications, "send_email", _send_email)
    database = _FakeDatabase(
        broadcaster_profile=SimpleNamespace(email="broadcaster@example.com", email_is_verified=True)
    )
    client = _make_client(monkeypatch, tmp_path, database, broadcaster_id=_BROADCASTER_ID)

    assert _upload(client) == 303

    assert len(sent_emails) == 1
    to_address, subject, context = sent_emails[0]
    assert to_address == "broadcaster@example.com"
    assert subject == "New Soundboard Clip Upload"
    assert isinstance(context, NewPendingClipEmailContext)
    assert context.dashboard_url == "http://testserver/admin/pending-clips"


def test_upload_succeeds_if_broadcaster_cannot_be_resolved(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    database = _FakeDatabase(broadcaster_profile=None)
    client = _make_client(monkeypatch, tmp_path, database, broadcaster_id=None)

    assert _upload(client) == 303

    assert database.pending_clips == ["<i>boom</i>"]
    assert database.notifications == []

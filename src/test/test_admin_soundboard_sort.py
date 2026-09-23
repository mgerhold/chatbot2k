"""Tests for issue #209: sorting the admin soundboard list by name or upload date,
ascending or descending. Drives the real FastAPI route + real Jinja templates."""

import os
import time
from pathlib import Path
from typing import Final

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from chatbot2k.database.tables import SoundboardCommand as DbSoundboardCommand
from chatbot2k.dependencies import get_app_state
from chatbot2k.dependencies import get_broadcaster_user
from chatbot2k.dependencies import get_common_context
from chatbot2k.routes import admin
from chatbot2k.routes import viewer
from chatbot2k.types.template_contexts import CommonContext
from chatbot2k.types.user_info import UserInfo
from chatbot2k.utils import soundboard as soundboard_utils


class _FakeDatabase:
    def __init__(self, commands: list[DbSoundboardCommand]) -> None:
        self._commands: Final = commands

    def get_soundboard_commands(self) -> list[DbSoundboardCommand]:
        return self._commands


class _FakeAppState:
    def __init__(self, database: _FakeDatabase) -> None:
        self.database = database
        self.command_handlers: list[object] = []


def _make_client(tmp_path: Path, commands: list[DbSoundboardCommand]) -> TestClient:
    admin.SOUNDBOARD_FILES_DIRECTORY = tmp_path  # type: ignore[assignment]
    soundboard_utils.SOUNDBOARD_FILES_DIRECTORY = tmp_path  # type: ignore[assignment]

    app = FastAPI()
    app.include_router(admin.router)
    app.include_router(viewer.router)
    app.dependency_overrides[get_app_state] = lambda: _FakeAppState(_FakeDatabase(commands))
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


def _make_commands_with_mtimes(tmp_path: Path) -> list[DbSoundboardCommand]:
    """Creates three clips named out of alphabetical order, with file mtimes also
    out of order relative to their names, so name-sort and date-sort disagree."""
    specs = [
        # (command name, filename, mtime offset in seconds)
        ("charlie", "charlie.mp3", 200),
        ("alpha", "alpha.mp3", 100),
        ("bravo", "bravo.mp3", 300),
    ]
    now = time.time()
    commands: list[DbSoundboardCommand] = []
    for name, filename, offset in specs:
        file_path = tmp_path / filename
        file_path.write_bytes(b"fake audio")
        mtime = now + offset
        os.utime(file_path, (mtime, mtime))
        commands.append(
            DbSoundboardCommand(
                name=name,
                filename=filename,
                uploader_twitch_id=None,
                uploader_twitch_login=None,
                uploader_twitch_display_name=None,
            )
        )
    return commands


def _command_order(html: str, names: list[str]) -> list[str]:
    positions = {name: html.index(f'value="{name}"') for name in names}
    return sorted(names, key=lambda name: positions[name])


def test_default_sort_is_name_ascending(tmp_path: Path) -> None:
    commands = _make_commands_with_mtimes(tmp_path)
    client = _make_client(tmp_path, commands)

    response = client.get("/admin/soundboard")

    assert response.status_code == 200
    assert _command_order(response.text, ["alpha", "bravo", "charlie"]) == ["alpha", "bravo", "charlie"]


def test_sort_by_name_descending(tmp_path: Path) -> None:
    commands = _make_commands_with_mtimes(tmp_path)
    client = _make_client(tmp_path, commands)

    response = client.get("/admin/soundboard", params={"sort_by": "name", "order": "desc"})

    assert response.status_code == 200
    assert _command_order(response.text, ["alpha", "bravo", "charlie"]) == ["charlie", "bravo", "alpha"]


def test_sort_by_date_ascending(tmp_path: Path) -> None:
    commands = _make_commands_with_mtimes(tmp_path)
    client = _make_client(tmp_path, commands)

    response = client.get("/admin/soundboard", params={"sort_by": "date", "order": "asc"})

    assert response.status_code == 200
    # alpha=100s, charlie=200s, bravo=300s -> oldest to newest.
    assert _command_order(response.text, ["alpha", "bravo", "charlie"]) == ["alpha", "charlie", "bravo"]


def test_sort_by_date_descending(tmp_path: Path) -> None:
    commands = _make_commands_with_mtimes(tmp_path)
    client = _make_client(tmp_path, commands)

    response = client.get("/admin/soundboard", params={"sort_by": "date", "order": "desc"})

    assert response.status_code == 200
    assert _command_order(response.text, ["alpha", "bravo", "charlie"]) == ["bravo", "charlie", "alpha"]


def test_missing_clip_file_does_not_crash_date_sort(tmp_path: Path) -> None:
    commands = [
        DbSoundboardCommand(
            name="ghost",
            filename="does-not-exist.mp3",
            uploader_twitch_id=None,
            uploader_twitch_login=None,
            uploader_twitch_display_name=None,
        )
    ]
    client = _make_client(tmp_path, commands)

    response = client.get("/admin/soundboard", params={"sort_by": "date", "order": "asc"})

    assert response.status_code == 200
    assert 'value="ghost"' in response.text


@pytest.mark.parametrize(
    ("current_sort_by", "current_order", "expected_next_order"),
    [
        ("name", "asc", "desc"),
        ("name", "desc", "asc"),
        ("date", "asc", "asc"),
    ],
)
def test_command_header_toggles_order_correctly(
    tmp_path: Path,
    current_sort_by: str,
    current_order: str,
    expected_next_order: str,
) -> None:
    commands = _make_commands_with_mtimes(tmp_path)
    client = _make_client(tmp_path, commands)

    response = client.get("/admin/soundboard", params={"sort_by": current_sort_by, "order": current_order})

    assert response.status_code == 200
    assert f"?sort_by=name&amp;order={expected_next_order}" in response.text

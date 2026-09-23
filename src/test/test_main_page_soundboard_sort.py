"""Tests for sorting the publicly visible soundboard list on the main page by name
or upload date, ascending or descending, and for the active tab surviving the
resulting full-page reload (issue #209 follow-up)."""

import os
import time
from pathlib import Path
from typing import cast

from fastapi import FastAPI
from fastapi.testclient import TestClient

from chatbot2k.app_state import AppState
from chatbot2k.command_handlers.clip_handler import ClipHandler
from chatbot2k.dependencies import get_app_state
from chatbot2k.dependencies import get_common_context
from chatbot2k.routes import commands
from chatbot2k.routes import viewer
from chatbot2k.types.template_contexts import CommonContext
from chatbot2k.utils import soundboard as soundboard_utils


class _FakeDatabase:
    def get_constants(self) -> list[object]:
        return []


class _FakeDictionary:
    def as_dict(self) -> dict[str, str]:
        return {}


def _make_clip_handler(name: str, filename: str) -> ClipHandler:
    return ClipHandler(cast(AppState, object()), name=name, filename=filename, volume=1.0)


def _make_client(
    tmp_path: Path,
    handlers: list[ClipHandler],
    *,
    is_soundboard_enabled: bool = True,
) -> TestClient:
    soundboard_utils.SOUNDBOARD_FILES_DIRECTORY = tmp_path  # type: ignore[assignment]

    app_state_mock = type(
        "FakeAppState",
        (),
        {
            "command_handlers": handlers,
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


def _make_handlers_with_mtimes(tmp_path: Path) -> list[ClipHandler]:
    """Creates three clips named out of alphabetical order, with file mtimes also
    out of order relative to their names, so name-sort and date-sort disagree."""
    specs = [
        # (command name, filename, mtime offset in seconds)
        ("charlie", "charlie.mp3", 200),
        ("alpha", "alpha.mp3", 100),
        ("bravo", "bravo.mp3", 300),
    ]
    now = time.time()
    handlers: list[ClipHandler] = []
    for name, filename, offset in specs:
        file_path = tmp_path / filename
        file_path.write_bytes(b"fake audio")
        mtime = now + offset
        os.utime(file_path, (mtime, mtime))
        handlers.append(_make_clip_handler(name, filename))
    return handlers


def _command_order(html: str, names: list[str]) -> list[str]:
    positions = {name: html.index(f"!{name}") for name in names}
    return sorted(names, key=lambda name: positions[name])


def test_default_sort_is_name_ascending(tmp_path: Path) -> None:
    handlers = _make_handlers_with_mtimes(tmp_path)
    client = _make_client(tmp_path, handlers)

    response = client.get("/")

    assert response.status_code == 200
    assert _command_order(response.text, ["alpha", "bravo", "charlie"]) == ["alpha", "bravo", "charlie"]


def test_sort_by_name_descending(tmp_path: Path) -> None:
    handlers = _make_handlers_with_mtimes(tmp_path)
    client = _make_client(tmp_path, handlers)

    response = client.get("/", params={"section": "soundboard", "sort_by": "name", "order": "desc"})

    assert response.status_code == 200
    assert _command_order(response.text, ["alpha", "bravo", "charlie"]) == ["charlie", "bravo", "alpha"]


def test_sort_by_date_ascending(tmp_path: Path) -> None:
    handlers = _make_handlers_with_mtimes(tmp_path)
    client = _make_client(tmp_path, handlers)

    response = client.get("/", params={"section": "soundboard", "sort_by": "date", "order": "asc"})

    assert response.status_code == 200
    # alpha=100s, charlie=200s, bravo=300s -> oldest to newest.
    assert _command_order(response.text, ["alpha", "bravo", "charlie"]) == ["alpha", "charlie", "bravo"]


def test_sort_by_date_descending(tmp_path: Path) -> None:
    handlers = _make_handlers_with_mtimes(tmp_path)
    client = _make_client(tmp_path, handlers)

    response = client.get("/", params={"section": "soundboard", "sort_by": "date", "order": "desc"})

    assert response.status_code == 200
    assert _command_order(response.text, ["alpha", "bravo", "charlie"]) == ["bravo", "charlie", "alpha"]


def test_soundboard_tab_stays_active_after_sorting(tmp_path: Path) -> None:
    handlers = _make_handlers_with_mtimes(tmp_path)
    client = _make_client(tmp_path, handlers)

    response = client.get("/", params={"section": "soundboard", "sort_by": "date", "order": "desc"})

    assert response.status_code == 200
    assert 'id="tab-soundboard" checked' in response.text
    assert 'id="tab-commands" checked' not in response.text


def test_commands_tab_is_active_by_default(tmp_path: Path) -> None:
    handlers = _make_handlers_with_mtimes(tmp_path)
    client = _make_client(tmp_path, handlers)

    response = client.get("/")

    assert response.status_code == 200
    assert 'id="tab-commands" checked' in response.text
    assert 'id="tab-soundboard" checked' not in response.text

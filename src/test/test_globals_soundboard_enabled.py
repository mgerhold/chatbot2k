"""Tests for issue #113: toggling Globals.is_soundboard_enabled broadcasts a
SoundboardStateEvent to every registered admin SSE listener, so open admin tabs and
the chat command (!soundboard enable|disable, which just assigns this same property)
converge on one notification path."""

import asyncio
from typing import Final
from uuid import uuid4

from chatbot2k.globals import Globals
from chatbot2k.models.soundboard_state_event import SoundboardStateEvent


def _make_bare_globals(*, initially_enabled: bool) -> Globals:
    """Constructs a Globals instance without running its (heavy, I/O-touching)
    __init__, then manually sets up only the attributes this feature touches."""
    instance: Final = Globals.__new__(Globals)
    instance._is_soundboard_enabled = initially_enabled  # type: ignore[reportPrivateUsage]
    instance._soundboard_state_event_queues = {}  # type: ignore[reportPrivateUsage]
    return instance


def test_setting_the_same_value_does_not_broadcast() -> None:
    globals_: Final = _make_bare_globals(initially_enabled=True)
    queue: Final = asyncio.Queue[SoundboardStateEvent]()
    globals_.soundboard_state_event_queues[uuid4()] = queue

    globals_.is_soundboard_enabled = True

    assert queue.empty()


def test_disabling_broadcasts_to_all_registered_queues() -> None:
    globals_: Final = _make_bare_globals(initially_enabled=True)
    queue_a: Final = asyncio.Queue[SoundboardStateEvent]()
    queue_b: Final = asyncio.Queue[SoundboardStateEvent]()
    globals_.soundboard_state_event_queues[uuid4()] = queue_a
    globals_.soundboard_state_event_queues[uuid4()] = queue_b

    globals_.is_soundboard_enabled = False

    assert globals_.is_soundboard_enabled is False
    assert queue_a.get_nowait() == SoundboardStateEvent(is_enabled=False)
    assert queue_b.get_nowait() == SoundboardStateEvent(is_enabled=False)


def test_re_enabling_broadcasts_the_new_value() -> None:
    globals_: Final = _make_bare_globals(initially_enabled=False)
    queue: Final = asyncio.Queue[SoundboardStateEvent]()
    globals_.soundboard_state_event_queues[uuid4()] = queue

    globals_.is_soundboard_enabled = True

    assert queue.get_nowait() == SoundboardStateEvent(is_enabled=True)


def test_no_registered_listeners_does_not_raise() -> None:
    globals_: Final = _make_bare_globals(initially_enabled=True)

    globals_.is_soundboard_enabled = False  # should not raise despite no queues registered

    assert globals_.is_soundboard_enabled is False

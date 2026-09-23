"""Tests for the public soundboard status SSE stream (GET /soundboard/events).
Whether the soundboard is enabled isn't sensitive information, so this stream lives
outside the broadcaster-gated /admin router and is reachable by anyone - only
actually changing the state (POST /admin/soundboard/enabled) requires admin auth."""

import asyncio
from collections.abc import AsyncIterator
from typing import cast

import pytest
from starlette.requests import Request

from chatbot2k.app_state import AppState
from chatbot2k.models.soundboard_state_event import SoundboardStateEvent
from chatbot2k.routes import commands


class _FakeAppState:
    def __init__(self) -> None:
        self.soundboard_state_event_queues: dict[object, asyncio.Queue[SoundboardStateEvent]] = {}
        self.is_shutting_down = asyncio.Event()


class _FakeRequest:
    def __init__(self) -> None:
        self.disconnected = False

    async def is_disconnected(self) -> bool:
        return self.disconnected


@pytest.mark.asyncio
async def test_events_stream_registers_and_cleans_up_a_queue() -> None:
    app_state = _FakeAppState()
    request = _FakeRequest()

    response = await commands.soundboard_events(cast(Request, request), cast(AppState, app_state))
    body_iterator = cast(AsyncIterator[bytes], response.body_iterator)

    async def _next_chunk() -> bytes:
        return await anext(body_iterator)

    # The first chunk runs `_generate()` up to its first suspension point. Since the
    # queue starts empty, that's the 1s keep-alive wait, so we run it as a background
    # task and only wait until the queue has actually been registered.
    pending_chunk = asyncio.create_task(_next_chunk())
    await asyncio.sleep(0)
    assert len(app_state.soundboard_state_event_queues) == 1
    queue_id, queue = next(iter(app_state.soundboard_state_event_queues.items()))
    queue.put_nowait(SoundboardStateEvent(is_enabled=False))

    chunk = await pending_chunk
    assert b"is_enabled" in chunk
    assert b"false" in chunk.lower()

    # Simulate the client disconnecting, which should stop the loop and clean up the queue.
    request.disconnected = True
    with pytest.raises(StopAsyncIteration):
        await _next_chunk()
    assert queue_id not in app_state.soundboard_state_event_queues

"""Tests for how core.py wires automatic shoutouts (issue #124) into message processing
and resets the session when the monitored channel goes live, mirroring entrance sounds."""

from typing import Final
from typing import cast
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import pytest

from chatbot2k.app_state import AppState
from chatbot2k.chats.chat import Chat
from chatbot2k.core import _handle_channel_going_live  # type: ignore[reportPrivateUsage]
from chatbot2k.core import _process_chat_message  # type: ignore[reportPrivateUsage]
from chatbot2k.types.chat_message import ChatMessage
from chatbot2k.types.chat_response import ChatResponse
from chatbot2k.types.live_notification import StreamLiveEvent
from chatbot2k.types.permission_level import PermissionLevel


@pytest.mark.asyncio
async def test_shoutout_is_triggered_after_processing_a_regular_message() -> None:
    app_state: Final = MagicMock()
    app_state.lookup_command.return_value = None
    app_state.dictionary.get_explanations.return_value = None

    shoutout_command: Final = AsyncMock()
    chat_message: Final = ChatMessage(
        text="hello!",
        sender_name="some_user",
        sender_chat=cast(Chat, MagicMock()),
        sender_permission_level=PermissionLevel.VIEWER,
        meta_data=None,
    )

    async def callback(chat_responses: list[ChatResponse], chat: Chat) -> None:
        pass

    await _process_chat_message(
        chat_message,
        cast(AppState, app_state),
        callback,
        cast(Chat, MagicMock()),
        entrance_sound_to_play=None,
        shoutout_to_give=shoutout_command,
    )

    shoutout_command.trigger.assert_awaited_once()


@pytest.mark.asyncio
async def test_channel_going_live_for_own_broadcaster_resets_shoutout_session() -> None:
    app_state: Final = MagicMock()
    app_state.config.twitch_channel = "some_broadcaster"
    app_state.database.get_live_notification_channels.return_value = []
    event: Final = StreamLiveEvent(
        broadcaster_id="1",
        broadcaster_name="Some Broadcaster",
        broadcaster_login="some_broadcaster",
        stream_title="",
        game_name="",
        thumbnail_url="",
    )

    await _handle_channel_going_live(cast(AppState, app_state), event, [])

    app_state.entrance_sound_handler.reset_entrance_sounds_session.assert_called_once()
    app_state.automatic_shoutout_handler.reset_automatic_shoutouts_session.assert_called_once()


@pytest.mark.asyncio
async def test_channel_going_live_for_other_broadcaster_does_not_reset_shoutout_session() -> None:
    app_state: Final = MagicMock()
    app_state.config.twitch_channel = "some_broadcaster"
    app_state.database.get_live_notification_channels.return_value = []
    event: Final = StreamLiveEvent(
        broadcaster_id="2",
        broadcaster_name="Someone Else",
        broadcaster_login="someone_else",
        stream_title="",
        game_name="",
        thumbnail_url="",
    )

    await _handle_channel_going_live(cast(AppState, app_state), event, [])

    app_state.entrance_sound_handler.reset_entrance_sounds_session.assert_not_called()
    app_state.automatic_shoutout_handler.reset_automatic_shoutouts_session.assert_not_called()

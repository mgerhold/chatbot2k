"""Tests for how core.py handles `SendTwitchBroadcastCommand`s, which are used by otherwise unrelated
components (e.g. the web interface) to post messages to the Twitch chat while the stream is live."""

from typing import Final
from typing import cast
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import pytest

from chatbot2k.chats.chat import Chat
from chatbot2k.chats.discord_chat import DiscordChat
from chatbot2k.chats.twitch_chat import TwitchChat
from chatbot2k.core import _handle_send_twitch_broadcast_command  # type: ignore[reportPrivateUsage]
from chatbot2k.types.broadcast_message import BroadcastMessage
from chatbot2k.types.commands import SendTwitchBroadcastCommand

# The URL must not be rewritten into "url (url)" by the Markdown-to-text preprocessing.
_MESSAGE: Final = BroadcastMessage(text="@the_broadcaster Hello! See https://example.com/viewer/soundboard")


@pytest.mark.asyncio
async def test_message_is_sent_unchanged_to_twitch_chat_only() -> None:
    twitch_chat: Final = MagicMock(spec=TwitchChat)
    twitch_chat.send_broadcast = AsyncMock()
    discord_chat: Final = MagicMock(spec=DiscordChat)
    discord_chat.send_broadcast = AsyncMock()

    await _handle_send_twitch_broadcast_command(
        SendTwitchBroadcastCommand(_MESSAGE),
        [cast(Chat, discord_chat), cast(Chat, twitch_chat)],
    )

    twitch_chat.send_broadcast.assert_awaited_once_with(_MESSAGE)
    discord_chat.send_broadcast.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_twitch_chat_is_ignored() -> None:
    discord_chat: Final = MagicMock(spec=DiscordChat)
    discord_chat.send_broadcast = AsyncMock()

    await _handle_send_twitch_broadcast_command(SendTwitchBroadcastCommand(_MESSAGE), [cast(Chat, discord_chat)])

    discord_chat.send_broadcast.assert_not_awaited()


@pytest.mark.asyncio
async def test_errors_while_sending_are_not_propagated() -> None:
    twitch_chat: Final = MagicMock(spec=TwitchChat)
    twitch_chat.send_broadcast = AsyncMock(side_effect=RuntimeError("Twitch API unavailable"))

    # Must not raise, since this would end the command handling loop.
    await _handle_send_twitch_broadcast_command(SendTwitchBroadcastCommand(_MESSAGE), [cast(Chat, twitch_chat)])

    twitch_chat.send_broadcast.assert_awaited_once_with(_MESSAGE)

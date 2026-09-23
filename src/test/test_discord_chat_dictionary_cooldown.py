"""Tests for DiscordChat's dictionary explanation cooldown (issue #146): message-count
based (rather than time-based, like Twitch), tracked independently per Discord channel,
configurable via ConfigurationSettingKind.DICTIONARY_DISCORD_COOLDOWN_MESSAGES."""

import asyncio
from typing import Final
from typing import cast
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import pytest

from chatbot2k.chats.discord_chat import DiscordChat
from chatbot2k.chats.discord_chat import DiscordChatMessage
from chatbot2k.models.discord_chat_message_metadata import DiscordChatMessageMetadata
from chatbot2k.types.chat_message import ChatMessage
from chatbot2k.types.configuration_setting_kind import ConfigurationSettingKind
from chatbot2k.types.permission_level import PermissionLevel


def _make_chat(app_state: MagicMock) -> DiscordChat:
    client: Final = MagicMock()
    client.start = AsyncMock()
    return DiscordChat(client, asyncio.Queue(), "token", app_state, DiscordChat._Passkey())  # type: ignore[reportPrivateUsage]


def _make_message_for_channel(channel_id: int, chat: DiscordChat) -> ChatMessage:
    discord_message: Final = MagicMock()
    discord_message.channel.id = channel_id
    return ChatMessage(
        text="FOO",
        sender_name="some_user",
        sender_chat=chat,
        sender_permission_level=PermissionLevel.VIEWER,
        meta_data=DiscordChatMessageMetadata(message=discord_message),
    )


@pytest.mark.asyncio
async def test_word_stays_in_cooldown_until_the_configured_number_of_messages_pass() -> None:
    app_state: Final = MagicMock()
    app_state.database.retrieve_configuration_setting_or_default.return_value = "2"
    chat: Final = _make_chat(app_state)
    message: Final = _make_message_for_channel(111, chat)
    counts = cast(dict[int, int], chat._dictionary_message_counts)  # type: ignore[reportPrivateUsage]

    counts[111] = 10
    chat.record_dictionary_explanation_shown("FOO", message)

    assert not chat.should_show_dictionary_explanation("FOO", message)  # 0 messages have passed

    counts[111] = 11  # 1 message passed
    assert not chat.should_show_dictionary_explanation("FOO", message)

    counts[111] = 12  # 2 messages passed -> cooldown lifted
    assert chat.should_show_dictionary_explanation("FOO", message)


@pytest.mark.asyncio
async def test_cooldown_is_independent_per_channel() -> None:
    app_state: Final = MagicMock()
    app_state.database.retrieve_configuration_setting_or_default.return_value = "20"
    chat: Final = _make_chat(app_state)
    message_a: Final = _make_message_for_channel(111, chat)
    message_b: Final = _make_message_for_channel(222, chat)

    chat.record_dictionary_explanation_shown("FOO", message_a)

    assert not chat.should_show_dictionary_explanation("FOO", message_a)
    assert chat.should_show_dictionary_explanation("FOO", message_b)


@pytest.mark.asyncio
async def test_non_discord_metadata_always_allows_the_explanation() -> None:
    app_state: Final = MagicMock()
    chat: Final = _make_chat(app_state)
    message: Final = ChatMessage(
        text="FOO",
        sender_name="some_user",
        sender_chat=chat,
        sender_permission_level=PermissionLevel.VIEWER,
        meta_data=None,
    )

    assert chat.should_show_dictionary_explanation("FOO", message)
    chat.record_dictionary_explanation_shown("FOO", message)  # should not raise


@pytest.mark.asyncio
async def test_cooldown_messages_are_read_from_configuration_with_the_default_fallback() -> None:
    app_state: Final = MagicMock()
    app_state.database.retrieve_configuration_setting_or_default.return_value = "20"
    chat: Final = _make_chat(app_state)
    message: Final = _make_message_for_channel(111, chat)

    # The configured cooldown is only consulted once a word has actually been shown before.
    chat.record_dictionary_explanation_shown("FOO", message)
    chat.should_show_dictionary_explanation("FOO", message)

    app_state.database.retrieve_configuration_setting_or_default.assert_called_once_with(
        ConfigurationSettingKind.DICTIONARY_DISCORD_COOLDOWN_MESSAGES, "20"
    )


@pytest.mark.asyncio
async def test_get_message_stream_increments_the_per_channel_message_count() -> None:
    app_state: Final = MagicMock()
    chat: Final = _make_chat(app_state)
    discord_message: Final = MagicMock()
    discord_message.channel.id = 111
    queue = cast(asyncio.Queue[DiscordChatMessage], chat._chat_message_queue)  # type: ignore[reportPrivateUsage]

    stream = chat.get_message_stream()
    await queue.put(
        DiscordChatMessage(
            text="hello",
            sender_name="some_user",
            sender_permission_level=PermissionLevel.VIEWER,
            meta_data=DiscordChatMessageMetadata(message=discord_message),
        )
    )
    await anext(stream)

    counts = cast(dict[int, int], chat._dictionary_message_counts)  # type: ignore[reportPrivateUsage]
    assert counts[111] == 1

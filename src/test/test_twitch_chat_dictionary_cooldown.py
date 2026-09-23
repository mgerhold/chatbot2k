"""Tests for TwitchChat's dictionary explanation cooldown (issue #146): time-based,
mirroring the pre-refactor behavior, now configurable via
ConfigurationSettingKind.DICTIONARY_TWITCH_COOLDOWN_SECONDS."""

from typing import Final
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from chatbot2k.chats.twitch_chat import TwitchChat
from chatbot2k.types.chat_message import ChatMessage
from chatbot2k.types.configuration_setting_kind import ConfigurationSettingKind
from chatbot2k.types.permission_level import PermissionLevel


def _make_chat(app_state: MagicMock) -> TwitchChat:
    return TwitchChat(MagicMock(), channel="somechannel", bot_user=MagicMock(), app_state=app_state)


def _make_message(chat: TwitchChat) -> ChatMessage:
    return ChatMessage(
        text="FOO",
        sender_name="some_user",
        sender_chat=chat,
        sender_permission_level=PermissionLevel.VIEWER,
        meta_data=None,
    )


@pytest.mark.asyncio
async def test_word_is_allowed_before_ever_being_shown() -> None:
    app_state: Final = MagicMock()
    app_state.database.retrieve_configuration_setting_or_default.return_value = "60"
    chat: Final = _make_chat(app_state)

    assert chat.should_show_dictionary_explanation("FOO", _make_message(chat))


@pytest.mark.asyncio
async def test_word_is_in_cooldown_immediately_after_being_shown() -> None:
    app_state: Final = MagicMock()
    app_state.database.retrieve_configuration_setting_or_default.return_value = "60"
    chat: Final = _make_chat(app_state)
    message: Final = _make_message(chat)

    with patch("chatbot2k.chats.twitch_chat.time.monotonic", return_value=100.0):
        chat.record_dictionary_explanation_shown("FOO", message)
        assert not chat.should_show_dictionary_explanation("FOO", message)


@pytest.mark.asyncio
async def test_cooldown_lifts_after_the_configured_number_of_seconds() -> None:
    app_state: Final = MagicMock()
    app_state.database.retrieve_configuration_setting_or_default.return_value = "60"
    chat: Final = _make_chat(app_state)
    message: Final = _make_message(chat)

    with patch("chatbot2k.chats.twitch_chat.time.monotonic", side_effect=[100.0, 159.0, 160.0]):
        chat.record_dictionary_explanation_shown("FOO", message)  # recorded at t=100.0
        assert not chat.should_show_dictionary_explanation("FOO", message)  # t=159.0, only 59s passed
        assert chat.should_show_dictionary_explanation("FOO", message)  # t=160.0, 60s passed


@pytest.mark.asyncio
async def test_cooldown_seconds_are_read_from_configuration_with_the_default_fallback() -> None:
    app_state: Final = MagicMock()
    app_state.database.retrieve_configuration_setting_or_default.return_value = "60"
    chat: Final = _make_chat(app_state)
    message: Final = _make_message(chat)

    # The configured cooldown is only consulted once a word has actually been shown before.
    chat.record_dictionary_explanation_shown("FOO", message)
    chat.should_show_dictionary_explanation("FOO", message)

    app_state.database.retrieve_configuration_setting_or_default.assert_called_once_with(
        ConfigurationSettingKind.DICTIONARY_TWITCH_COOLDOWN_SECONDS, "60.0"
    )

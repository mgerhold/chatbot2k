"""Regression test for issue #214: managing dictionary entries should not immediately
echo the entry's explanation, since the command message itself contains the word."""

from typing import Final
from typing import cast
from unittest.mock import MagicMock

import pytest

from chatbot2k.app_state import AppState
from chatbot2k.chats.chat import Chat
from chatbot2k.command_handlers.dictionary_handler import DictionaryHandler
from chatbot2k.core import _process_chat_message  # type: ignore[reportPrivateUsage]
from chatbot2k.types.chat_message import ChatMessage
from chatbot2k.types.chat_response import ChatResponse
from chatbot2k.types.permission_level import PermissionLevel


def _make_app_state(dictionary_entries: dict[str, str]) -> MagicMock:
    dictionary: Final = MagicMock()
    dictionary.as_dict.return_value = dict(dictionary_entries)
    # If `get_explanations` were called for a dictionary command, this would surface as an
    # extra response and the test would catch it.
    dictionary.get_explanations.return_value = [
        ChatResponse(text="FOO: should never be echoed here", chat_message=cast(ChatMessage, MagicMock()))
    ]

    app_state_mock: Final = MagicMock()
    app_state_mock.dictionary = dictionary

    handler: Final = DictionaryHandler(cast(AppState, app_state_mock))
    app_state_mock.lookup_command.return_value = handler
    return app_state_mock


@pytest.mark.asyncio
async def test_dict_add_does_not_echo_the_new_entry() -> None:
    app_state: Final = _make_app_state({})
    chat_message: Final = ChatMessage(
        text='!dict add FOO "some explanation"',
        sender_name="moderator",
        sender_chat=cast(Chat, MagicMock()),
        sender_permission_level=PermissionLevel.MODERATOR,
        meta_data=None,
    )
    responses: list[ChatResponse] = []

    async def callback(chat_responses: list[ChatResponse], chat: Chat) -> None:
        responses.extend(chat_responses)

    await _process_chat_message(
        chat_message,
        cast(AppState, app_state),
        callback,
        cast(Chat, MagicMock()),
        entrance_sound_to_play=None,
    )

    assert len(responses) == 1
    assert responses[0].text == "Added 'FOO' to the dictionary."
    app_state.dictionary.get_explanations.assert_not_called()


@pytest.mark.asyncio
async def test_dict_update_does_not_echo_the_entry() -> None:
    app_state: Final = _make_app_state({"FOO": "an existing explanation"})
    chat_message: Final = ChatMessage(
        text='!dict update FOO "a new explanation"',
        sender_name="moderator",
        sender_chat=cast(Chat, MagicMock()),
        sender_permission_level=PermissionLevel.MODERATOR,
        meta_data=None,
    )
    responses: list[ChatResponse] = []

    async def callback(chat_responses: list[ChatResponse], chat: Chat) -> None:
        responses.extend(chat_responses)

    await _process_chat_message(
        chat_message,
        cast(AppState, app_state),
        callback,
        cast(Chat, MagicMock()),
        entrance_sound_to_play=None,
    )

    assert len(responses) == 1
    assert responses[0].text == "Updated 'FOO' in the dictionary."
    app_state.dictionary.get_explanations.assert_not_called()

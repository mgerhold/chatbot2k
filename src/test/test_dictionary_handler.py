"""Tests for DictionaryHandler's !dict subcommands, notably !dict append (issue #211)."""

from typing import Final
from typing import cast
from unittest.mock import MagicMock

import pytest

from chatbot2k.app_state import AppState
from chatbot2k.chats.chat import Chat
from chatbot2k.command_handlers.dictionary_handler import DictionaryHandler
from chatbot2k.types.chat_command import ChatCommand
from chatbot2k.types.chat_message import ChatMessage


def _make_command(*arguments: str) -> ChatCommand:
    return ChatCommand(
        name=DictionaryHandler.COMMAND_NAME,
        arguments=list(arguments),
        source_message=cast(ChatMessage, MagicMock()),
        source_chat=cast(Chat, MagicMock()),
    )


def _make_handler(entries: dict[str, str]) -> tuple[DictionaryHandler, MagicMock]:
    dictionary: Final = MagicMock()
    dictionary.as_dict.return_value = dict(entries)
    app_state_mock: Final = MagicMock()
    app_state_mock.dictionary = dictionary
    return DictionaryHandler(cast(AppState, app_state_mock)), dictionary


@pytest.mark.asyncio
async def test_append_extends_existing_explanation() -> None:
    handler, dictionary = _make_handler({"FOO": "an existing explanation"})

    responses = await handler.handle_command(_make_command("append", "FOO", "and more"))

    assert responses is not None
    assert len(responses) == 1
    assert "Appended to 'FOO'" in responses[0].text
    dictionary.update_entry.assert_called_once_with(
        word="FOO",
        new_explanation="an existing explanation and more",
    )


@pytest.mark.asyncio
async def test_append_is_case_insensitive_and_preserves_stored_case() -> None:
    handler, dictionary = _make_handler({"FOO": "an existing explanation"})

    responses = await handler.handle_command(_make_command("append", "foo", "and more"))

    assert responses is not None
    assert "Appended to 'FOO'" in responses[0].text
    dictionary.update_entry.assert_called_once_with(
        word="FOO",
        new_explanation="an existing explanation and more",
    )


@pytest.mark.asyncio
async def test_append_to_unknown_word_reports_error_without_mutating() -> None:
    handler, dictionary = _make_handler({})

    responses = await handler.handle_command(_make_command("append", "FOO", "and more"))

    assert responses is not None
    assert "Cannot append to 'FOO'" in responses[0].text
    dictionary.update_entry.assert_not_called()


@pytest.mark.asyncio
async def test_append_requires_exactly_word_and_text() -> None:
    handler, dictionary = _make_handler({"FOO": "an existing explanation"})

    responses = await handler.handle_command(_make_command("append", "FOO"))

    assert responses is None
    dictionary.update_entry.assert_not_called()

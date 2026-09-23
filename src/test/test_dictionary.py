"""Tests for Dictionary's cooldown delegation (issue #146): Dictionary no longer owns
any cooldown state or strategy itself - it asks the message's sender_chat whether to
show an explanation, and tells it when one was shown, letting each platform own its
own cooldown strategy (e.g. time-based for Twitch, per-channel message-count-based
for Discord)."""

from collections.abc import AsyncGenerator
from collections.abc import Sequence
from typing import Final
from typing import cast
from unittest.mock import MagicMock

from chatbot2k.chats.chat import Chat
from chatbot2k.database.tables import DictionaryEntry as DbDictionaryEntry
from chatbot2k.dictionary import Dictionary
from chatbot2k.types.broadcast_message import BroadcastMessage
from chatbot2k.types.chat_message import ChatMessage
from chatbot2k.types.chat_platform import ChatPlatform
from chatbot2k.types.chat_response import ChatResponse
from chatbot2k.types.live_notification import LiveNotification
from chatbot2k.types.permission_level import PermissionLevel
from chatbot2k.types.shoutout_command import ShoutoutCommand


class _FakeChat(Chat):
    def __init__(self, *, allowed_words: set[str]) -> None:
        self._allowed_words: Final = allowed_words
        self.shown_words: list[str] = []

    async def get_message_stream(self) -> AsyncGenerator[ChatMessage]:
        return
        yield  # pragma: no cover - unreachable; only needed to satisfy the abstract signature

    async def send_responses(self, responses: Sequence[ChatResponse]) -> None:
        raise NotImplementedError

    async def send_broadcast(self, message: BroadcastMessage) -> None:
        raise NotImplementedError

    async def post_live_notification(self, notification: LiveNotification) -> None:
        raise NotImplementedError

    async def react_to_raid(self, message: BroadcastMessage) -> None:
        raise NotImplementedError

    async def shoutout(self, command: ShoutoutCommand) -> None:
        raise NotImplementedError

    @property
    def platform(self) -> ChatPlatform:
        return ChatPlatform.MOCK

    def should_show_dictionary_explanation(self, word: str, chat_message: ChatMessage) -> bool:
        return word in self._allowed_words

    def record_dictionary_explanation_shown(self, word: str, chat_message: ChatMessage) -> None:
        self.shown_words.append(word)


def _make_dictionary(entries: dict[str, str]) -> Dictionary:
    database: Final = MagicMock()
    database.get_dictionary_entries.return_value = [
        DbDictionaryEntry(word=word, explanation=explanation) for word, explanation in entries.items()
    ]
    return Dictionary(database)


def _make_message(text: str, chat: Chat) -> ChatMessage:
    return ChatMessage(
        text=text,
        sender_name="some_user",
        sender_chat=chat,
        sender_permission_level=PermissionLevel.VIEWER,
        meta_data=None,
    )


def test_matching_word_is_explained_when_chat_allows_it() -> None:
    dictionary: Final = _make_dictionary({"FOO": "some explanation"})
    chat: Final = _FakeChat(allowed_words={"FOO"})

    responses = dictionary.get_explanations(_make_message("what does FOO mean?", chat))

    assert responses is not None
    assert len(responses) == 1
    assert responses[0].text == "FOO: some explanation"
    assert chat.shown_words == ["FOO"]


def test_matching_word_is_not_explained_when_chat_is_in_cooldown() -> None:
    dictionary: Final = _make_dictionary({"FOO": "some explanation"})
    chat: Final = _FakeChat(allowed_words=set())

    responses = dictionary.get_explanations(_make_message("what does FOO mean?", chat))

    assert responses is None
    assert chat.shown_words == []


def test_cooldown_is_only_reset_for_entries_within_the_display_cap() -> None:
    words: Final = ["FOO", "BAR", "BAZ", "QUX", "QUUX"]
    dictionary: Final = _make_dictionary({word: f"explanation for {word}" for word in words})
    chat: Final = _FakeChat(allowed_words=set(words))

    responses = dictionary.get_explanations(_make_message(" ".join(words), chat))

    assert responses is not None
    # 5 matches exceed the cap of 4, so only 3 explanations + 1 "note" message are shown...
    assert len(responses) == 4
    assert "Note: Only the first 3 explanations are shown." in responses[-1].text
    # ...and only those first 3 (displayed) words have their cooldown reset, matching the
    # pre-existing behavior before this refactor (truncation happens before cooldown is recorded).
    assert chat.shown_words == words[:3]


def test_remove_entry_only_takes_a_word() -> None:
    dictionary: Final = _make_dictionary({"FOO": "some explanation"})
    chat: Final = _FakeChat(allowed_words={"FOO"})

    dictionary.remove_entry("FOO")

    responses = dictionary.get_explanations(_make_message("what does FOO mean?", chat))
    assert responses is None
    cast(MagicMock, dictionary._database).remove_dictionary_entry_case_insensitive.assert_called_once_with(  # type: ignore[reportPrivateUsage]
        word="FOO"
    )

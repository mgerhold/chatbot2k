"""Tests for AutomaticShoutoutHandler (issue #124): giving a user an automatic shoutout
the first time they chat during a stream session, mirroring the entrance sound mechanic."""

from typing import Final
from typing import Optional
from typing import cast
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from chatbot2k.app_state import AppState
from chatbot2k.automatic_shoutouts import AutomaticShoutoutHandler
from chatbot2k.chats.chat import Chat
from chatbot2k.database.tables import AutomaticShoutout
from chatbot2k.models.twitch_chat_message_metadata import TwitchChatMessageMetadata
from chatbot2k.types.chat_message import ChatMessage
from chatbot2k.types.permission_level import PermissionLevel
from chatbot2k.types.shoutout_command import ShoutoutCommand
from chatbot2k.utils.twitch import TwitchUserInfo


def _make_twitch_chat_message(sender_twitch_user_id: str) -> ChatMessage:
    twitch_message: Final = MagicMock()
    twitch_message.user.id = sender_twitch_user_id
    return ChatMessage(
        text="hello!",
        sender_name="some_user",
        sender_chat=cast(Chat, MagicMock()),
        sender_permission_level=PermissionLevel.VIEWER,
        meta_data=TwitchChatMessageMetadata(message=twitch_message),
    )


def _make_app_state(*, configured_user_ids: set[str]) -> MagicMock:
    def _get_automatic_shoutout_by_twitch_user_id(*, twitch_user_id: str) -> Optional[AutomaticShoutout]:
        return AutomaticShoutout(twitch_user_id=twitch_user_id) if twitch_user_id in configured_user_ids else None

    app_state_mock: Final = MagicMock()
    app_state_mock.config.twitch_channel = "some_broadcaster"
    app_state_mock.database.get_automatic_shoutout_by_twitch_user_id.side_effect = (
        _get_automatic_shoutout_by_twitch_user_id
    )
    return app_state_mock


@pytest.mark.asyncio
async def test_returns_none_for_non_twitch_messages() -> None:
    handler: Final = AutomaticShoutoutHandler(cast(AppState, _make_app_state(configured_user_ids={"123"})))
    chat_message: Final = ChatMessage(
        text="hello!",
        sender_name="some_user",
        sender_chat=cast(Chat, MagicMock()),
        sender_permission_level=PermissionLevel.VIEWER,
        meta_data=None,
    )

    result = await handler.get_shoutout_to_give(chat_message, cast(Chat, MagicMock()))

    assert result is None


@pytest.mark.asyncio
async def test_returns_none_when_user_not_configured() -> None:
    handler: Final = AutomaticShoutoutHandler(cast(AppState, _make_app_state(configured_user_ids=set())))
    chat_message: Final = _make_twitch_chat_message("123")

    result = await handler.get_shoutout_to_give(chat_message, cast(Chat, MagicMock()))

    assert result is None


@pytest.mark.asyncio
async def test_gives_shoutout_and_resolves_broadcaster_id_on_trigger() -> None:
    app_state: Final = _make_app_state(configured_user_ids={"123"})
    handler: Final = AutomaticShoutoutHandler(cast(AppState, app_state))
    chat_message: Final = _make_twitch_chat_message("123")
    chat: Final = MagicMock()
    chat.shoutout = AsyncMock()

    with patch(
        "chatbot2k.automatic_shoutouts.get_twitch_user_by_login",
        new=AsyncMock(
            return_value=TwitchUserInfo(id="999", login="some_broadcaster", display_name="", profile_image_url="")
        ),
    ) as mocked_lookup:
        command = await handler.get_shoutout_to_give(chat_message, cast(Chat, chat))
        assert command is not None
        await command.trigger()

    mocked_lookup.assert_awaited_once_with("some_broadcaster", app_state)
    chat.shoutout.assert_awaited_once_with(ShoutoutCommand(from_broadcaster_id="999", to_broadcaster_id="123"))


@pytest.mark.asyncio
async def test_does_not_shoutout_again_within_the_same_session() -> None:
    app_state: Final = _make_app_state(configured_user_ids={"123"})
    handler: Final = AutomaticShoutoutHandler(cast(AppState, app_state))
    chat_message: Final = _make_twitch_chat_message("123")
    chat: Final = MagicMock()
    chat.shoutout = AsyncMock()

    with patch(
        "chatbot2k.automatic_shoutouts.get_twitch_user_by_login",
        new=AsyncMock(
            return_value=TwitchUserInfo(id="999", login="some_broadcaster", display_name="", profile_image_url="")
        ),
    ):
        first_command = await handler.get_shoutout_to_give(chat_message, cast(Chat, chat))
        assert first_command is not None
        await first_command.trigger()

        second_result = await handler.get_shoutout_to_give(chat_message, cast(Chat, chat))

    assert second_result is None
    chat.shoutout.assert_awaited_once()


@pytest.mark.asyncio
async def test_reset_session_allows_shoutout_again() -> None:
    app_state: Final = _make_app_state(configured_user_ids={"123"})
    handler: Final = AutomaticShoutoutHandler(cast(AppState, app_state))
    chat_message: Final = _make_twitch_chat_message("123")
    chat: Final = MagicMock()
    chat.shoutout = AsyncMock()

    with patch(
        "chatbot2k.automatic_shoutouts.get_twitch_user_by_login",
        new=AsyncMock(
            return_value=TwitchUserInfo(id="999", login="some_broadcaster", display_name="", profile_image_url="")
        ),
    ):
        first_command = await handler.get_shoutout_to_give(chat_message, cast(Chat, chat))
        assert first_command is not None
        await first_command.trigger()

        handler.reset_automatic_shoutouts_session()

        second_command = await handler.get_shoutout_to_give(chat_message, cast(Chat, chat))

    assert second_command is not None


@pytest.mark.asyncio
async def test_does_not_shoutout_when_broadcaster_id_cannot_be_resolved() -> None:
    app_state: Final = _make_app_state(configured_user_ids={"123"})
    handler: Final = AutomaticShoutoutHandler(cast(AppState, app_state))
    chat_message: Final = _make_twitch_chat_message("123")
    chat: Final = MagicMock()
    chat.shoutout = AsyncMock()

    with patch(
        "chatbot2k.automatic_shoutouts.get_twitch_user_by_login",
        new=AsyncMock(return_value=None),
    ):
        command = await handler.get_shoutout_to_give(chat_message, cast(Chat, chat))
        assert command is not None
        await command.trigger()

    chat.shoutout.assert_not_awaited()

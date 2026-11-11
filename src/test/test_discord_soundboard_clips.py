"""Tests for posting soundboard clips to Discord: the clip is uploaded as a
regular message, or linked if it exceeds the upload limit of the guild."""

import asyncio
import logging
from pathlib import Path
from typing import Final
from typing import Optional
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import discord
import pytest

from chatbot2k.chats.discord_chat import DiscordChat
from chatbot2k.chats.mock_chat import MockChat
from chatbot2k.command_handlers.clip_handler import ClipHandler
from chatbot2k.constants import SOUNDBOARD_FILES_DIRECTORY
from chatbot2k.models.discord_chat_message_metadata import DiscordChatMessageMetadata
from chatbot2k.types.chat_command import ChatCommand
from chatbot2k.types.chat_message import ChatMessage
from chatbot2k.types.chat_response import ChatAttachment
from chatbot2k.types.chat_response import ChatResponse
from chatbot2k.types.feature_flags import FeatureFlags
from chatbot2k.types.feature_flags import FormattingSupport
from chatbot2k.types.permission_level import PermissionLevel


def _make_discord_chat() -> DiscordChat:
    client: Final = MagicMock()
    client.start = AsyncMock()
    return DiscordChat(client, asyncio.Queue(), "token", MagicMock(), DiscordChat._Passkey())  # type: ignore[reportPrivateUsage]


def _make_discord_message(*, filesize_limit: Optional[int]) -> MagicMock:
    message: Final = MagicMock()
    message.channel.send = AsyncMock()
    if filesize_limit is None:
        message.guild = None
    else:
        message.guild.filesize_limit = filesize_limit
    return message


def _make_chat_message(chat: DiscordChat, discord_message: MagicMock) -> ChatMessage:
    return ChatMessage(
        text="!clip",
        sender_name="some_user",
        sender_chat=chat,
        sender_permission_level=PermissionLevel.VIEWER,
        meta_data=DiscordChatMessageMetadata(message=discord_message),
    )


def test_discord_can_post_soundboard_clips_but_not_trigger_the_soundboard() -> None:
    flags: Final = _make_discord_chat().feature_flags
    assert flags.can_post_soundboard_clips
    assert not flags.can_trigger_soundboard


@pytest.mark.asyncio
@pytest.mark.parametrize("is_soundboard_enabled", [True, False])
async def test_clip_handler_returns_attachment_on_discord_regardless_of_whether_soundboard_is_disabled(
    is_soundboard_enabled: bool,
) -> None:
    app_state: Final = MagicMock()
    app_state.is_soundboard_enabled = is_soundboard_enabled
    app_state.enqueue_soundboard_clip_url = AsyncMock()
    app_state.config.twitch_redirect_uri = "https://bot.example.com/auth/twitch/callback"
    chat: Final = _make_discord_chat()
    message: Final = _make_chat_message(chat, _make_discord_message(filesize_limit=10))
    handler: Final = ClipHandler(app_state, name="clip", filename="abc.mp4", volume=0.5)

    responses: Final = await handler.handle_command(
        ChatCommand(
            name="clip",
            arguments=[],
            source_message=message,
            source_chat=chat,
        )
    )

    assert responses == [
        ChatResponse(
            text="",
            chat_message=message,
            attachment=ChatAttachment(
                path=SOUNDBOARD_FILES_DIRECTORY / "abc.mp4",
                url="https://bot.example.com/static/soundboard/abc.mp4",
            ),
        )
    ]
    app_state.enqueue_soundboard_clip_url.assert_not_called()


@pytest.mark.asyncio
async def test_clip_handler_still_triggers_soundboard_and_posts_nothing_on_twitch() -> None:
    app_state: Final = MagicMock()
    app_state.enqueue_soundboard_clip_url = AsyncMock()
    twitch_like_chat: Final = MockChat(
        FeatureFlags(
            regular_chat=True,
            broadcasting=True,
            formatting_support=FormattingSupport.NONE,
            can_post_live_notifications=False,
            can_react_to_raids=True,
            can_shoutout=True,
            can_trigger_soundboard=True,
            can_post_soundboard_clips=False,
            can_trigger_entrance_sounds=True,
            supports_giveaways=True,
        )
    )
    message: Final = ChatMessage(
        text="!clip",
        sender_name="user",
        sender_chat=twitch_like_chat,
        sender_permission_level=PermissionLevel.VIEWER,
        meta_data=None,
    )
    handler: Final = ClipHandler(app_state, name="clip", filename="abc.mp4", volume=0.5)

    responses: Final = await handler.handle_command(
        ChatCommand(
            name="clip",
            arguments=[],
            source_message=message,
            source_chat=twitch_like_chat,
        )
    )

    assert responses == []
    app_state.enqueue_soundboard_clip_url.assert_awaited_once_with("/static/soundboard/abc.mp4", 0.5)


@pytest.mark.asyncio
async def test_small_clip_is_uploaded_as_file(tmp_path: Path) -> None:
    clip: Final = tmp_path / "clip.mp4"
    clip.write_bytes(b"12345")
    chat: Final = _make_discord_chat()
    discord_message: Final = _make_discord_message(filesize_limit=10)
    response: Final = ChatResponse(
        text="",
        chat_message=_make_chat_message(chat, discord_message),
        attachment=ChatAttachment(path=clip, url="http://x/clip.mp4"),
    )

    await chat.send_responses([response])

    discord_message.channel.send.assert_awaited_once()
    kwargs: Final = discord_message.channel.send.await_args.kwargs
    assert kwargs["content"] is None
    assert isinstance(kwargs["file"], discord.File)


@pytest.mark.asyncio
@pytest.mark.parametrize("filesize_limit", [4, None])
async def test_oversized_clip_is_posted_as_link(tmp_path: Path, filesize_limit: Optional[int]) -> None:
    clip: Final = tmp_path / "clip.mp4"
    clip.write_bytes(b"x" * (11 * 1024 * 1024) if filesize_limit is None else b"12345")
    chat: Final = _make_discord_chat()
    discord_message: Final = _make_discord_message(filesize_limit=filesize_limit)
    response: Final = ChatResponse(
        text="",
        chat_message=_make_chat_message(chat, discord_message),
        attachment=ChatAttachment(path=clip, url="http://x/clip.mp4"),
    )

    await chat.send_responses([response])

    discord_message.channel.send.assert_awaited_once_with("http://x/clip.mp4")


@pytest.mark.asyncio
async def test_missing_clip_file_posts_nothing_and_logs_an_error(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    chat: Final = _make_discord_chat()
    discord_message: Final = _make_discord_message(filesize_limit=10)
    response: Final = ChatResponse(
        text="",
        chat_message=_make_chat_message(chat, discord_message),
        attachment=ChatAttachment(path=tmp_path / "missing.mp4", url="http://x/missing.mp4"),
    )

    with caplog.at_level(logging.ERROR, logger="chatbot2k.chats.discord_chat"):
        await chat.send_responses([response])

    discord_message.channel.send.assert_not_called()
    error_records: Final = [record for record in caplog.records if record.levelno == logging.ERROR]
    assert len(error_records) == 1
    assert "missing.mp4" in error_records[0].getMessage()

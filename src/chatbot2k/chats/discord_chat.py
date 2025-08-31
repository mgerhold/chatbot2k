import asyncio
import logging
from collections.abc import AsyncGenerator
from collections.abc import Sequence
from typing import Any
from typing import Final
from typing import NamedTuple
from typing import Optional
from typing import Self
from typing import final
from typing import override

import discord
from discord import Client
from discord import Message

from chatbot2k.app_state import AppState
from chatbot2k.chats.chat import Chat
from chatbot2k.models.discord_chat_message_metadata import DiscordChatMessageMetadata
from chatbot2k.types.broadcast_message import BroadcastMessage
from chatbot2k.types.chat_message import ChatMessage
from chatbot2k.types.chat_platform import ChatPlatform
from chatbot2k.types.chat_response import ChatResponse
from chatbot2k.types.feature_flags import FeatureFlags
from chatbot2k.types.feature_flags import FormattingSupport
from chatbot2k.types.permission_level import PermissionLevel


# This is just a helper type because of how this module is structured. It is
# almost identical to the `ChatMessage` type, but it's only missing the
# `sender_chat` field, because this cannot be known inside the
# `_DiscordClient` class.
@final
class DiscordChatMessage(NamedTuple):
    text: str
    sender_name: str
    sender_permission_level: PermissionLevel
    meta_data: Any  # Platform-specific metadata.

    def to_chat_message(self, sender_chat: Chat) -> ChatMessage:
        return ChatMessage(
            text=self.text,
            sender_name=self.sender_name,
            sender_chat=sender_chat,
            sender_permission_level=self.sender_permission_level,
            meta_data=self.meta_data,
        )


@final
class _DiscordClient(Client):
    def __init__(
        self,
        *,
        intents: discord.Intents,
        chat_message_queue: asyncio.Queue[DiscordChatMessage],
    ) -> None:
        super().__init__(intents=intents)
        self._chat_message_queue: Final = chat_message_queue

    async def on_ready(self) -> None:
        logging.info(f"Connected to Discord as user {self.user}.")

    async def on_message(self, message: Message) -> None:
        if message.author == self.user:
            return
        permissions_level = PermissionLevel.VIEWER
        if isinstance(message.author, discord.Member):
            if message.author.guild_permissions.administrator:
                permissions_level = PermissionLevel.ADMIN
        await self._chat_message_queue.put(
            DiscordChatMessage(
                text=message.content,
                sender_name=message.author.name,
                sender_permission_level=permissions_level,
                meta_data=DiscordChatMessageMetadata(message=message),
            )
        )


@final
class DiscordChat(Chat):
    def __init__(
        self,
        client: _DiscordClient,
        chat_message_queue: asyncio.Queue[DiscordChatMessage],
        discord_token: str,
    ) -> None:
        super().__init__(
            FeatureFlags(
                regular_chat=True,
                broadcasting=False,
                formatting_support=FormattingSupport.MARKDOWN,
                can_trigger_soundboard=False,
            )
        )
        self._client: Final = client
        self._chat_message_queue: Final = chat_message_queue
        self._client_task: Optional[asyncio.Task] = None
        self._discord_token: Final = discord_token

    async def _ensure_started(self) -> None:
        if self._client_task is None or self._client_task.done():
            self._client_task = asyncio.create_task(self._client.start(self._discord_token))

    @override
    async def get_message_stream(self) -> AsyncGenerator[ChatMessage]:
        await self._ensure_started()
        while True:
            yield (await self._chat_message_queue.get()).to_chat_message(self)

    @override
    async def send_responses(self, responses: Sequence[ChatResponse]) -> None:
        for response in responses:
            metadata = response.chat_message.meta_data
            if not isinstance(metadata, DiscordChatMessageMetadata):
                logging.error("Response metadata is not of type DiscordChatMessageMetadata. Unable to respond.")
                continue
            await metadata.message.channel.send(response.text)

    @override
    async def send_broadcast(self, message: BroadcastMessage) -> None:
        raise NotImplementedError()

    @property
    @override
    def platform(self) -> ChatPlatform:
        return ChatPlatform.DISCORD

    @classmethod
    async def create(cls, app_state: AppState) -> Self:
        intents: Final = discord.Intents.default()
        intents.message_content = True
        chat_message_queue: Final[asyncio.Queue[DiscordChatMessage]] = asyncio.Queue()

        client: Final = _DiscordClient(
            intents=intents,
            chat_message_queue=chat_message_queue,
        )
        instance = cls(client, chat_message_queue, app_state.config.discord_token)
        await instance._ensure_started()
        return instance

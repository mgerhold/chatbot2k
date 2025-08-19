import asyncio
import logging
from collections.abc import AsyncGenerator
from collections.abc import Sequence
from typing import Final
from typing import Optional
from typing import Self
from typing import final
from typing import override

import discord
from discord import Client
from discord import Message

from chatbot2k.chats.chat import Chat
from chatbot2k.config import CONFIG
from chatbot2k.models.discord_chat_message_metadata import DiscordChatMessageMetadata
from chatbot2k.types.broadcast_message import BroadcastMessage
from chatbot2k.types.chat_message import ChatMessage
from chatbot2k.types.chat_response import ChatResponse
from chatbot2k.types.feature_flags import ChatFeatures
from chatbot2k.types.permission_level import PermissionLevel


@final
class _DiscordClient(Client):
    def __init__(
        self,
        *,
        intents: discord.Intents,
        chat_message_queue: asyncio.Queue[ChatMessage],
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
            ChatMessage(
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
        chat_message_queue: asyncio.Queue[ChatMessage],
    ) -> None:
        super().__init__(
            ChatFeatures(
                REGULAR_CHAT=True,
                BROADCASTING=False,
            )
        )
        self._client: Final = client
        self._chat_message_queue: Final = chat_message_queue
        self._client_task: Optional[asyncio.Task] = None

    async def _ensure_started(self) -> None:
        if self._client_task is None or self._client_task.done():
            self._client_task = asyncio.create_task(self._client.start(CONFIG.discord_token))

    @override
    async def get_message_stream(self) -> AsyncGenerator[ChatMessage]:
        await self._ensure_started()
        while True:
            message: ChatMessage = await self._chat_message_queue.get()
            yield message

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

    @classmethod
    async def create(cls) -> Self:
        intents: Final = discord.Intents.default()
        intents.message_content = True
        chat_message_queue: Final[asyncio.Queue[ChatMessage]] = asyncio.Queue()

        client: Final = _DiscordClient(
            intents=intents,
            chat_message_queue=chat_message_queue,
        )
        instance = cls(client, chat_message_queue)
        await instance._ensure_started()
        return instance

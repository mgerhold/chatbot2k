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
from chatbot2k.types.live_notification import LiveNotification
from chatbot2k.types.permission_level import PermissionLevel

logger: Final = logging.getLogger(__name__)


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
        moderator_role_id: Optional[int],
    ) -> None:
        super().__init__(intents=intents)
        self._chat_message_queue: Final = chat_message_queue
        self._moderator_role_id: Final = moderator_role_id

    async def on_ready(self) -> None:
        logging.info(f"Connected to Discord as user {self.user}.")

    async def on_message(self, message: Message) -> None:
        if message.author == self.user:
            return
        permissions_level = PermissionLevel.VIEWER
        if isinstance(message.author, discord.Member):
            if message.author.guild_permissions.administrator:
                permissions_level = PermissionLevel.ADMIN
            elif self._moderator_role_id is not None and any(
                role.id == self._moderator_role_id for role in message.author.roles
            ):
                permissions_level = PermissionLevel.MODERATOR
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
    @final
    class _Passkey: ...

    def __init__(
        self,
        client: _DiscordClient,
        chat_message_queue: asyncio.Queue[DiscordChatMessage],
        discord_token: str,
        _: _Passkey,
    ) -> None:
        super().__init__(
            FeatureFlags(
                regular_chat=True,
                broadcasting=False,
                formatting_support=FormattingSupport.MARKDOWN,
                can_post_live_notifications=True,
                can_trigger_soundboard=False,
                supports_giveaways=False,
            )
        )
        self._client: Final = client
        self._chat_message_queue: Final = chat_message_queue
        self._client_task: Optional[asyncio.Task[None]] = None
        self._discord_token: Final = discord_token
        self._text_channels_by_name: dict[str, discord.TextChannel] = {}

    @classmethod
    async def create(cls, app_state: AppState) -> Self:
        intents: Final = discord.Intents.default()
        intents.message_content = True
        chat_message_queue: Final[asyncio.Queue[DiscordChatMessage]] = asyncio.Queue()

        client: Final = _DiscordClient(
            intents=intents,
            chat_message_queue=chat_message_queue,
            moderator_role_id=app_state.config.discord_moderator_role_id,
        )
        instance: Final = cls(
            client,
            chat_message_queue,
            app_state.config.discord_token,
            DiscordChat._Passkey(),
        )
        await instance._ensure_started()
        return instance

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
            try:
                await metadata.message.channel.send(response.text)
            except Exception as e:
                try:
                    await metadata.message.channel.send(f"Unable to send message: {e}")
                except Exception:
                    logging.error(f"Unable to send error message to channel: {e}")

    @override
    async def send_broadcast(self, message: BroadcastMessage) -> None:
        raise NotImplementedError

    @override
    async def post_live_notification(self, notification: LiveNotification) -> None:
        await self._ensure_started()
        channel = self._text_channels_by_name.get(notification.target_channel)
        if channel is None:
            # Maybe the channels have changed since we last checked or have not been collected yet;
            # refresh the list.
            self._text_channels_by_name = DiscordChat._get_writable_text_channels(self._client)
            channel = self._text_channels_by_name.get(notification.target_channel)

        if channel is None:
            logger.error(
                f"Unable to post live notification: No writable channel named '{notification.target_channel}' found."
            )
            return

        text_to_send: Final = notification.render_text()
        try:
            await channel.send(text_to_send)
        except Exception as e:
            logger.exception(f"Unable to post live notification to channel '{notification.target_channel}': {e}")

    @property
    @override
    def platform(self) -> ChatPlatform:
        return ChatPlatform.DISCORD

    async def _ensure_started(self) -> None:
        if self._client_task is None or self._client_task.done():
            self._client_task = asyncio.create_task(self._client.start(self._discord_token))

    @staticmethod
    def _get_writable_text_channels(client: _DiscordClient) -> dict[str, discord.TextChannel]:
        text_channels_by_name: Final[dict[str, discord.TextChannel]] = {}
        for channel in client.get_all_channels():
            if not isinstance(channel, discord.TextChannel):
                continue
            me = channel.guild.me
            permissions = channel.permissions_for(me)
            if not permissions.view_channel or not permissions.send_messages:
                continue
            if channel.name in text_channels_by_name:
                logging.warning(
                    f"Multiple writable text channels with the name '{channel.name}' found. Using one arbitrarily."
                )
            text_channels_by_name[channel.name] = channel
        return text_channels_by_name

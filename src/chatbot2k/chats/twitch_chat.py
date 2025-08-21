import asyncio
import logging
from collections.abc import AsyncGenerator
from collections.abc import Sequence
from typing import Final
from typing import Self
from typing import final
from typing import override

from twitchAPI.chat import Chat as TwitchChatClient
from twitchAPI.chat import ChatMessage as TwitchChatMessage
from twitchAPI.chat import EventData
from twitchAPI.oauth import UserAuthenticator
from twitchAPI.twitch import Twitch
from twitchAPI.type import AuthScope
from twitchAPI.type import ChatEvent

from chatbot2k.app_state import AppState
from chatbot2k.chats.chat import Chat
from chatbot2k.models.twitch_chat_message_metadata import TwitchChatMessageMetadata
from chatbot2k.types.broadcast_message import BroadcastMessage
from chatbot2k.types.chat_message import ChatMessage
from chatbot2k.types.chat_response import ChatResponse
from chatbot2k.types.feature_flags import ChatFeatures
from chatbot2k.types.feature_flags import FormattingSupport
from chatbot2k.types.permission_level import PermissionLevel


@final
class TwitchChat(Chat):
    _SCOPES = [AuthScope.CHAT_READ, AuthScope.CHAT_EDIT]

    def __init__(self, client: TwitchChatClient, channel: str) -> None:
        super().__init__(
            ChatFeatures(
                regular_chat=True,
                broadcasting=True,
                formatting_support=FormattingSupport.NONE,
            ),
        )
        self._app_loop: Final = asyncio.get_running_loop()
        self._message_queue: Final[asyncio.Queue[ChatMessage]] = asyncio.Queue()
        self._channel: Final = channel

        async def _on_ready(ready_event: EventData) -> None:
            await self._on_ready(ready_event)

        async def _on_message(message: TwitchChatMessage) -> None:
            await self._on_message(message)

        client.register_event(ChatEvent.READY, _on_ready)
        client.register_event(ChatEvent.MESSAGE, _on_message)

        self._twitch_chat_client: Final = client
        self._twitch_chat_client.start()

    @classmethod
    async def create(cls, app_state: AppState) -> Self:
        async def _on_user_refresh(new_access_token: str, new_refresh_token: str) -> None:
            app_state.config.update_twitch_tokens(new_access_token, new_refresh_token)

        if app_state.config.twitch_credentials is None:
            # We only have the client secret, so we have to obtain tokens interactively.
            client = await Twitch(
                app_state.config.twitch_client_id,
                app_state.config.twitch_credentials,
            )
            client.user_auth_refresh_callback = _on_user_refresh
            auth: Final = UserAuthenticator(client, TwitchChat._SCOPES)
            auth_response: Final = await auth.authenticate()
            assert auth_response is not None
            access_token, refresh_token = auth_response
            print(f"Obtained tokens: {access_token}, {refresh_token}")
        else:
            # We already have tokens. Maybe the access token is expired, but we should
            # be able to refresh it.
            access_token, refresh_token = app_state.config.twitch_credentials
            client = await Twitch(
                app_state.config.twitch_client_id,
                app_state.config.twitch_client_secret,
                authenticate_app=False,
            )
            client.user_auth_refresh_callback = _on_user_refresh
        await client.set_user_authentication(
            access_token,
            TwitchChat._SCOPES,
            refresh_token,
            validate=True,
        )
        chat: Final = await TwitchChatClient(client)

        return cls(chat, app_state.config.twitch_channel)

    @override
    async def get_message_stream(self) -> AsyncGenerator[ChatMessage]:
        while True:
            message: ChatMessage = await self._message_queue.get()
            yield message

    @override
    async def send_responses(self, responses: Sequence[ChatResponse]) -> None:
        for response in responses:
            await self._send_message(response.text)

    @override
    async def send_broadcast(self, message: BroadcastMessage) -> None:
        logging.info(f"Sending broadcast message to Twitch chat: {message.text}")
        await self._send_message(message.text)

    async def _on_ready(self, ready_event: EventData) -> None:
        logging.info(f"Twitch chat client is ready. Going to join channel '{self._channel}'...")
        await ready_event.chat.join_room(self._channel)
        logging.info(f"Twitch chat client has joined channel '{self._channel}'.")

    async def _on_message(self, message: TwitchChatMessage) -> None:
        self._app_loop.call_soon_threadsafe(
            self._message_queue.put_nowait,
            ChatMessage(
                text=message.text,
                sender_name=message.user.name,
                sender_permission_level=(
                    PermissionLevel.ADMIN
                    if message.user.name == self._channel
                    else (PermissionLevel.MODERATOR if message.user.mod else PermissionLevel.VIEWER)
                ),
                meta_data=TwitchChatMessageMetadata(message=message),
            ),
        )

    async def _send_message(self, message: str) -> None:
        if not self._twitch_chat_client.is_ready():
            logging.warning("Twitch chat client is not ready. Cannot send message.")
            return
        logging.info(f"Sending message to Twitch chat: {message}")
        await self._twitch_chat_client.send_message(self._channel, message)

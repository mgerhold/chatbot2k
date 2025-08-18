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

from chatbot2k.chats.chat import Chat
from chatbot2k.config import OAuthTokens
from chatbot2k.config import TwitchClientSecret
from chatbot2k.types.broadcast_message import BroadcastMessage
from chatbot2k.types.chat_message import ChatMessage
from chatbot2k.types.chat_response import ChatResponse
from chatbot2k.types.feature_flags import ChatFeatures


@final
class TwitchChat(Chat):
    _SCOPES = [AuthScope.CHAT_READ, AuthScope.CHAT_EDIT]

    def __init__(self, client: TwitchChatClient, channel: str) -> None:
        super().__init__(
            ChatFeatures(
                REGULAR_CHAT=True,
                BROADCASTING=True,
            ),
        )
        self._app_loop: Final = asyncio.get_running_loop()
        self._message_queue: Final[asyncio.Queue[ChatMessage]] = asyncio.Queue()
        self._channel = channel

        async def _on_ready(ready_event: EventData) -> None:
            await self._on_ready(ready_event)

        async def _on_message(message: TwitchChatMessage) -> None:
            await self._on_message(message)

        client.register_event(ChatEvent.READY, _on_ready)
        client.register_event(ChatEvent.MESSAGE, _on_message)

        self._twitch_chat_client: Final = client
        self._twitch_chat_client.start()

    @classmethod
    async def create(
        cls,
        *,
        app_id: str,
        credentials: TwitchClientSecret | OAuthTokens,
        channel: str,
    ) -> Self:
        match credentials:
            case str():
                client = await Twitch(app_id, credentials)
                auth: Final = UserAuthenticator(client, TwitchChat._SCOPES)
                auth_response: Final = await auth.authenticate()
                assert auth_response is not None
                access_token, refresh_token = auth_response
                print(f"Obtained tokens: {access_token}, {refresh_token}")
                await client.set_user_authentication(access_token, TwitchChat._SCOPES, refresh_token, validate=True)
            case OAuthTokens(access_token, refresh_token):
                client = await Twitch(app_id, authenticate_app=False)
                await client.set_user_authentication(access_token, TwitchChat._SCOPES, refresh_token, validate=True)
        chat: Final = await TwitchChatClient(client)

        return cls(chat, channel)

    @override
    async def get_message_stream(self) -> AsyncGenerator[ChatMessage]:
        while True:
            message: ChatMessage = await self._message_queue.get()
            yield message

    @override
    async def send_responses(self, responses: Sequence[ChatResponse]) -> None:
        for response in responses:
            logging.info(f"Sending response to Twitch chat: {response.text}")
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
                meta_data=message,  # We include the platform-native message.
            ),
        )

    async def _send_message(self, message: str) -> None:
        if not self._twitch_chat_client.is_ready():
            logging.warning("Twitch chat client is not ready. Cannot send message.")
            return
        logging.info(f"Sending message to Twitch chat: {message}")
        await self._twitch_chat_client.send_message(self._channel, message)

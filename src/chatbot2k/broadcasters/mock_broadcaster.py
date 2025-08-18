import logging
from asyncio import sleep
from collections.abc import AsyncGenerator
from typing import final
from typing import override

from chatbot2k.broadcasters.broadcaster import Broadcaster
from chatbot2k.types.broadcast_message import BroadcastMessage
from chatbot2k.types.chat_message import ChatMessage


@final
class MockBroadcaster(Broadcaster):
    @override
    async def get_broadcasts_stream(self) -> AsyncGenerator[BroadcastMessage]:
        for i in range(3):
            await sleep(5.0)
            yield BroadcastMessage(
                text=f"Mock broadcast message {i + 1}",
            )

    @override
    async def on_chat_message_received(self, message: ChatMessage) -> None:
        logging.info(f"MockBroadcaster received chat message: {message.text}")

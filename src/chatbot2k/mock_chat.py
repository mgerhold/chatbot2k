import logging
import random
from asyncio import sleep
from collections.abc import AsyncGenerator
from typing import final
from typing import override

from chatbot2k.broadcast_message import BroadcastMessage
from chatbot2k.chat import Chat
from chatbot2k.chat_message import ChatMessage
from chatbot2k.chat_response import ChatResponse


@final
class MockChat(Chat):
    @override
    async def get_message_stream(self) -> AsyncGenerator[ChatMessage]:
        for i in range(5):
            await sleep(random.uniform(0.1, 0.5))
            yield ChatMessage(text=f"Mock message {i + 1}")

    @override
    async def send_response(self, response: ChatResponse) -> None:
        logging.info(f"Mock response sent: {response.text}")

    @override
    async def send_broadcast(self, message: BroadcastMessage) -> None:
        logging.info(f"Mock broadcast sent: {message.text}")

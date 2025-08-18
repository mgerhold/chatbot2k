import logging
import random
from asyncio import sleep
from collections.abc import AsyncGenerator
from collections.abc import Sequence
from typing import final
from typing import override

from chatbot2k.chats.chat import Chat
from chatbot2k.types.broadcast_message import BroadcastMessage
from chatbot2k.types.chat_message import ChatMessage
from chatbot2k.types.chat_response import ChatResponse


@final
class MockChat(Chat):
    @override
    async def get_message_stream(self) -> AsyncGenerator[ChatMessage]:
        for i in range(5):
            await sleep(random.uniform(0.1, 0.5))
            yield ChatMessage(
                text=f"Mock message {i + 1}",
                sender_name="mock_user",
                meta_data=None,
            )

    @override
    async def send_responses(self, responses: Sequence[ChatResponse]) -> None:
        for response in responses:
            logging.info(f"Mock response sent: {response.text}")

    @override
    async def send_broadcast(self, message: BroadcastMessage) -> None:
        logging.info(f"Mock broadcast sent: {message.text}")

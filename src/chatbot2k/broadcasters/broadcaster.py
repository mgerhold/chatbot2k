from abc import ABC
from abc import abstractmethod
from collections.abc import AsyncGenerator

from chatbot2k.types.broadcast_message import BroadcastMessage
from chatbot2k.types.chat_message import ChatMessage


class Broadcaster(ABC):
    @abstractmethod
    def get_broadcasts_stream(self) -> AsyncGenerator[BroadcastMessage]:
        pass

    @abstractmethod
    async def on_chat_message_received(self, message: ChatMessage) -> None:
        pass

from abc import ABC
from abc import abstractmethod
from collections.abc import AsyncGenerator

from chatbot2k.broadcast_message import BroadcastMessage
from chatbot2k.chat_message import ChatMessage
from chatbot2k.chat_response import ChatResponse
from chatbot2k.feature_flags import ChatFeatures


class Chat(ABC):
    def __init__(self, features: ChatFeatures) -> None:
        self._feature_flags = features

    @property
    def feature_flags(self) -> ChatFeatures:
        return self._feature_flags

    @abstractmethod
    def get_message_stream(self) -> AsyncGenerator[ChatMessage]:
        pass

    @abstractmethod
    async def send_response(self, response: ChatResponse) -> None:
        pass

    @abstractmethod
    async def send_broadcast(self, message: BroadcastMessage) -> None:
        pass

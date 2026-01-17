from abc import ABC
from abc import abstractmethod
from collections.abc import AsyncGenerator
from collections.abc import Sequence
from typing import final

from chatbot2k.types.broadcast_message import BroadcastMessage
from chatbot2k.types.chat_message import ChatMessage
from chatbot2k.types.chat_platform import ChatPlatform
from chatbot2k.types.chat_response import ChatResponse
from chatbot2k.types.feature_flags import FeatureFlags
from chatbot2k.types.live_notification import LiveNotification
from chatbot2k.types.shoutout_command import ShoutoutCommand


class Chat(ABC):
    def __init__(self, features: FeatureFlags) -> None:
        self._feature_flags = features

    @final
    @property
    def feature_flags(self) -> FeatureFlags:
        return self._feature_flags

    @abstractmethod
    def get_message_stream(self) -> AsyncGenerator[ChatMessage]: ...

    @abstractmethod
    async def send_responses(self, responses: Sequence[ChatResponse]) -> None: ...

    @abstractmethod
    async def send_broadcast(self, message: BroadcastMessage) -> None: ...

    @abstractmethod
    async def post_live_notification(self, notification: LiveNotification) -> None: ...

    @abstractmethod
    async def react_to_raid(self, message: BroadcastMessage) -> None: ...

    @abstractmethod
    async def shoutout(self, command: ShoutoutCommand) -> None: ...

    @property
    @abstractmethod
    def platform(self) -> ChatPlatform: ...

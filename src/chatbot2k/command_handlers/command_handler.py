from abc import ABC
from abc import abstractmethod
from typing import Optional

from chatbot2k.types.chat_command import ChatCommand
from chatbot2k.types.chat_response import ChatResponse
from chatbot2k.types.permission_level import PermissionLevel


class CommandHandler(ABC):
    @abstractmethod
    async def handle_command(self, chat_command: ChatCommand) -> Optional[list[ChatResponse]]:
        pass

    @property
    @abstractmethod
    def min_required_permission_level(self) -> PermissionLevel:
        pass

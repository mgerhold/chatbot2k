from abc import ABC
from abc import abstractmethod
from typing import Optional

from chatbot2k.types.chat_command import ChatCommand
from chatbot2k.types.chat_response import ChatResponse


class CommandHandler(ABC):
    @abstractmethod
    async def handle_command(self, chat_command: ChatCommand) -> Optional[ChatResponse]:
        pass

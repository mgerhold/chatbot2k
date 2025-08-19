from abc import ABC
from abc import abstractmethod
from typing import Final
from typing import Optional

from chatbot2k.app_state import AppState
from chatbot2k.types.chat_command import ChatCommand
from chatbot2k.types.chat_response import ChatResponse
from chatbot2k.types.permission_level import PermissionLevel


class CommandHandler(ABC):
    def __init__(self, app_state: AppState, *, name: str) -> None:
        self._app_state: Final = app_state
        self._name: Final = name

    @abstractmethod
    async def handle_command(self, chat_command: ChatCommand) -> Optional[list[ChatResponse]]:
        """
        Handle a chat command and return a list of chat responses. If the command is used
        in a wrong way, this function should return `None`. If there just should not be a
        response, the function should return an empty list.
        :param chat_command: The chat command to handle.
        :return: A list of responses or `None` if the command was used incorrectly.
        """
        pass

    @property
    @abstractmethod
    def min_required_permission_level(self) -> PermissionLevel:
        pass

    @property
    @abstractmethod
    def usage(self) -> str:
        pass

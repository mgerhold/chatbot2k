from abc import ABC
from abc import abstractmethod
from typing import Final
from typing import Optional
from typing import final

from greenery import Pattern  # type: ignore[reportMissingTypeStubs]

from chatbot2k.app_state import AppState
from chatbot2k.types.chat_command import ChatCommand
from chatbot2k.types.chat_response import ChatResponse
from chatbot2k.types.permission_level import PermissionLevel
from chatbot2k.utils.regular_expressions import parse_regular_expression


class CommandHandler(ABC):
    def __init__(self, app_state: AppState, *, name: str) -> None:
        self._app_state: Final = app_state
        self._name: Final = name
        # `name` can be a regular expression pattern. Therefore, we compile it into a pattern
        # object and store it.
        self._regular_expression: Final = parse_regular_expression(name)
        # We consider this command handler to be triggered by a regular expression if
        # there are multiple possible strings that could be used to trigger the command. For this,
        # we check if the regular expression leads to more than one possible match. This can be used
        # to avoid performing an expensive regex match instead of a simple string comparison.
        self._is_regular_expression: Final = (
            len(list(zip(range(2), self._regular_expression.strings(), strict=False))) > 1
        )

    @final
    @property
    def name(self) -> str:
        return self._name

    @final
    @property
    def regular_expression(self) -> Pattern:
        return self._regular_expression

    @final
    @property
    def is_regular_expression(self) -> bool:
        return self._is_regular_expression

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
    def usages(self) -> list[str]:
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        pass

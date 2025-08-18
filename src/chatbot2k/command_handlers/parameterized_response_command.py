from collections.abc import Sequence
from typing import Final
from typing import Optional
from typing import final
from typing import override

from chatbot2k.command_handlers.command_handler import CommandHandler
from chatbot2k.command_handlers.utils import replace_placeholders_in_message
from chatbot2k.types.chat_command import ChatCommand
from chatbot2k.types.chat_response import ChatResponse


@final
class ParameterizedResponseCommand(CommandHandler):
    def __init__(self, parameters: Sequence[str], format_string: str) -> None:
        self._placeholders: Final = list(parameters)
        self._format_string: Final = format_string

    @override
    async def handle_command(self, chat_command: ChatCommand) -> Optional[ChatResponse]:
        result: Final = self._inject_arguments(chat_command)
        if result is None:
            return None
        return ChatResponse(
            text=replace_placeholders_in_message(
                result,
                chat_command.source_message,
            )
        )

    def _inject_arguments(self, chat_command: ChatCommand) -> Optional[str]:
        """
        Injects the arguments from the chat command into the format string.
        Returns `None` if the number of arguments does not match the number
        of placeholders.
        :param chat_command: The chat command to process.
        :return: The formatted string with arguments injected, or `None` if
                 the number of arguments does not match.
        """
        if len(chat_command.arguments) != len(self._placeholders):
            return None
        replacements: Final = {
            f"{{{placeholder}}}": argument
            for placeholder, argument in zip(self._placeholders, chat_command.arguments, strict=True)
        }
        result = self._format_string
        for placeholder, replacement in replacements.items():
            result = result.replace(placeholder, replacement)

        return result

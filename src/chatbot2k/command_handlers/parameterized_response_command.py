from collections.abc import Sequence
from typing import Final
from typing import Optional
from typing import final
from typing import override

from chatbot2k.builtins import apply_builtins
from chatbot2k.chat_command import ChatCommand
from chatbot2k.chat_response import ChatResponse
from chatbot2k.command_handlers.command_handler import CommandHandler
from chatbot2k.constants import replace_constants


@final
class ParameterizedResponseCommand(CommandHandler):
    def __init__(self, parameters: Sequence[str], format_string: str) -> None:
        self._placeholders: Final = list(parameters)
        self._format_string: Final = format_string

    @override
    async def handle_command(self, chat_command: ChatCommand) -> Optional[ChatResponse]:
        replacements: dict[str, str] = {}
        if len(chat_command.arguments) != len(self._placeholders):
            return None
        for i, argument in enumerate(chat_command.arguments):
            replacements[f"{{{self._placeholders[i]}}}"] = argument
        result = self._format_string
        for placeholder, replacement in replacements.items():
            result = result.replace(placeholder, replacement)
        return ChatResponse(text=replace_constants(apply_builtins(result)))

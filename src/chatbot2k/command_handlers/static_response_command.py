from typing import Optional
from typing import final
from typing import override

from chatbot2k.builtins import apply_builtins
from chatbot2k.chat_command import ChatCommand
from chatbot2k.chat_response import ChatResponse
from chatbot2k.command_handlers.command_handler import CommandHandler
from chatbot2k.constants import replace_constants


@final
class StaticResponseCommand(CommandHandler):
    def __init__(self, *, response: str) -> None:
        self._response = response

    @override
    async def handle_command(self, chat_command: ChatCommand) -> Optional[ChatResponse]:
        if chat_command.arguments:
            # Arguments are not allowed for static response commands.
            return None
        return ChatResponse(text=replace_constants(apply_builtins(self._response)))

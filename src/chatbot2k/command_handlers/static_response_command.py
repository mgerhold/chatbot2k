from typing import Optional
from typing import final
from typing import override

from chatbot2k.app_state import AppState
from chatbot2k.command_handlers.command_handler import CommandHandler
from chatbot2k.command_handlers.utils import replace_placeholders_in_message
from chatbot2k.types.chat_command import ChatCommand
from chatbot2k.types.chat_response import ChatResponse
from chatbot2k.types.permission_level import PermissionLevel


@final
class StaticResponseCommand(CommandHandler):
    def __init__(
        self,
        app_state: AppState,
        *,
        name: str,
        response: str,
    ) -> None:
        super().__init__(app_state, name=name)
        self._response = response

    @override
    async def handle_command(self, chat_command: ChatCommand) -> Optional[list[ChatResponse]]:
        if chat_command.arguments:
            # Arguments are not allowed for static response commands.
            return None
        return [
            ChatResponse(
                text=replace_placeholders_in_message(
                    self._response,
                    chat_command.source_message,
                ),
            )
        ]

    @override
    @property
    def min_required_permission_level(self) -> PermissionLevel:
        return PermissionLevel.VIEWER

    @override
    @property
    def usage(self) -> str:
        return f"!{self._name}"

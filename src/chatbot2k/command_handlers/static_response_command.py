from typing import Final
from typing import Optional
from typing import final
from typing import override

from chatbot2k.app_state import AppState
from chatbot2k.builtins import Builtin
from chatbot2k.command_handlers.command_handler import CommandHandler
from chatbot2k.command_handlers.utils import replace_placeholders_in_message
from chatbot2k.types.chat_command import ChatCommand
from chatbot2k.types.chat_response import ChatResponse
from chatbot2k.types.permission_level import PermissionLevel
from chatbot2k.utils.markdown import quote_braced_with_backticks


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
        return [
            ChatResponse(
                text=replace_placeholders_in_message(
                    text=self._response,
                    source_message=chat_command.source_message,
                    constants=self._app_state.database.get_constants(),
                    config=self._app_state.config,
                ),
                chat_message=chat_command.source_message,
            )
        ]

    @property
    @override
    def min_required_permission_level(self) -> PermissionLevel:
        return PermissionLevel.VIEWER

    @property
    @override
    def usage(self) -> str:
        return f"!{self._name}"

    @property
    @override
    def description(self) -> str:
        names_to_quote: Final = {builtin.name for builtin in Builtin} | {
            constant.name for constant in self._app_state.database.get_constants()
        }
        return f"{quote_braced_with_backticks(self._response, only_these=names_to_quote)}"

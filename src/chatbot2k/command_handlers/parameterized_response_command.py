from collections.abc import Sequence
from typing import Final
from typing import Optional
from typing import final
from typing import override

from chatbot2k.app_state import AppState
from chatbot2k.broadcasters.utils import replace_constants
from chatbot2k.builtins import Builtin
from chatbot2k.command_handlers.command_handler import CommandHandler
from chatbot2k.command_handlers.utils import replace_placeholders_in_message
from chatbot2k.types.chat_command import ChatCommand
from chatbot2k.types.chat_response import ChatResponse
from chatbot2k.types.permission_level import PermissionLevel
from chatbot2k.utils.markdown import quote_braced_with_backticks


@final
class ParameterizedResponseCommand(CommandHandler):
    def __init__(
        self,
        *,
        app_state: AppState,
        name: str,
        parameters: Sequence[str],
        format_string: str,
    ) -> None:
        super().__init__(app_state, name=name)
        self._placeholders: Final = list(parameters)
        self._format_string: Final = format_string

    @override
    async def handle_command(self, chat_command: ChatCommand) -> Optional[list[ChatResponse]]:
        result: Final = self._inject_arguments(chat_command)
        if result is None:
            return None
        return [
            ChatResponse(
                text=replace_placeholders_in_message(
                    text=result,
                    source_message=chat_command.source_message,
                    constants=self._app_state.database.get_constants(),
                    app_state=self._app_state,
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
        return f"!{self._name} {' '.join(f'{{{placeholder}}}' for placeholder in self._placeholders)}"

    @property
    @override
    def description(self) -> str:
        builtin_names: Final = {builtin.name for builtin in Builtin}
        names_to_quote: Final = (
            builtin_names
            | {constant.name for constant in self._app_state.database.get_constants()}
            | set(self._placeholders)
        )

        suffix: Final = (
            "\n\n*Parameters of this command:* "
            + f"{', '.join(f'`{placeholder}`' for placeholder in self._placeholders)}"
        )

        without_replacements: Final = quote_braced_with_backticks(self._format_string, only_these=names_to_quote)
        with_replacements: Final = quote_braced_with_backticks(
            replace_constants(self._format_string, self._app_state.database.get_constants())
        )
        if without_replacements != with_replacements:
            return (
                f"{without_replacements}\n\n*Note: This response contains constants, it expands to:*\n\n"
                + f"{with_replacements}{suffix}"
            )

        return f"{with_replacements}{suffix}"

    def _inject_arguments(self, chat_command: ChatCommand) -> Optional[str]:
        """
        Injects the arguments from the chat command into the format string.
        Returns `None` if the number of arguments does not match the number
        of placeholders.
        :param chat_command: The chat command to process.
        :return: The formatted string with arguments injected, or `None` if
                 the number of arguments does not match.
        """
        if len(chat_command.arguments) < len(self._placeholders):
            return None
        replacements: Final = {
            f"{{{placeholder}}}": argument
            for placeholder, argument in zip(self._placeholders, chat_command.arguments, strict=False)
        }
        result = self._format_string
        for placeholder, replacement in replacements.items():
            result = result.replace(placeholder, replacement)

        return result

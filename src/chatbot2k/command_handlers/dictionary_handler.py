from typing import Final
from typing import Optional
from typing import final
from typing import override

from chatbot2k.app_state import AppState
from chatbot2k.command_handlers.command_handler import CommandHandler
from chatbot2k.types.chat_command import ChatCommand
from chatbot2k.types.chat_response import ChatResponse
from chatbot2k.types.permission_level import PermissionLevel


@final
class DictionaryHandler(CommandHandler):
    COMMAND_NAME = "dict"

    @override
    def __init__(self, app_state: AppState) -> None:
        super().__init__(app_state, name=DictionaryHandler.COMMAND_NAME)

    @override
    async def handle_command(self, chat_command: ChatCommand) -> Optional[list[ChatResponse]]:
        if not chat_command.arguments:
            # We need to at least know the subcommand.
            return None
        subcommand: Final = chat_command.arguments[0].lower()
        match subcommand:
            case "add" if len(chat_command.arguments) == 3:
                add_result: Final = self._add_dict_entry(chat_command)
                return [
                    ChatResponse(
                        text=add_result,
                        chat_message=chat_command.source_message,
                    )
                ]
            case "remove" if len(chat_command.arguments) == 2:
                remove_result: Final = self._remove_dict_entry(chat_command)
                return [
                    ChatResponse(
                        text=remove_result,
                        chat_message=chat_command.source_message,
                    )
                ]
            case _:
                return None

    @property
    @override
    def min_required_permission_level(self) -> PermissionLevel:
        return PermissionLevel.MODERATOR

    @property
    @override
    def usage(self) -> str:
        return f"!{self.COMMAND_NAME} [add|remove] <word> [explanation]"

    @property
    @override
    def description(self) -> str:
        return (
            "Manage the dictionary of words and their explanations. "
            + f"Use `!{DictionaryHandler.COMMAND_NAME} add` to add a word with its explanation and "
            + f"`!{DictionaryHandler.COMMAND_NAME} remove` to remove a word."
        )

    def _add_dict_entry(
        self,
        chat_command: ChatCommand,
    ) -> str:
        word: Final = chat_command.arguments[1]
        explanation: Final = chat_command.arguments[2]
        if word.lower() in (other.lower() for other in self._app_state.dictionary.as_dict()):
            return f"Cannot add '{word}': it already exists in the dictionary."
        self._app_state.dictionary.add_entry(
            word=word,
            explanation=explanation,
        )
        return f"Added '{word}' to the dictionary."

    def _remove_dict_entry(
        self,
        chat_command: ChatCommand,
    ) -> str:
        word: Final = chat_command.arguments[1].lower()
        if word not in (other.lower() for other in self._app_state.dictionary.as_dict()):
            return f"Cannot remove '{word}': it does not exist in the dictionary."
        self._app_state.dictionary.remove_entry(chat_command.source_chat.platform, word)
        return f"Removed '{word}' from the dictionary."

from typing import Final
from typing import Optional
from typing import final
from typing import override

from chatbot2k.broadcasters.broadcaster import Broadcaster
from chatbot2k.broadcasters.parser import parse_broadcasters
from chatbot2k.command_handlers.command_handler import CommandHandler
from chatbot2k.command_handlers.parser import parse_commands
from chatbot2k.config import CONFIG
from chatbot2k.dictionary import Dictionary
from chatbot2k.models.commands import CommandsModel
from chatbot2k.models.parameterized_response_command import ParameterizedResponseCommandModel
from chatbot2k.models.static_response_command import StaticResponseCommandModel
from chatbot2k.types.chat_command import ChatCommand
from chatbot2k.types.chat_response import ChatResponse
from chatbot2k.types.permission_level import PermissionLevel


@final
class Globals:
    def __init__(self) -> None:
        self._command_handlers = Globals._load_command_handlers(self)
        self._broadcasters = Globals._load_broadcasters()
        self._dictionary = Globals._load_dictionary()

    @property
    def command_handlers(self) -> dict[str, CommandHandler]:
        return self._command_handlers

    @property
    def broadcasters(self) -> list[Broadcaster]:
        return self._broadcasters

    @property
    def dictionary(self) -> Dictionary:
        return self._dictionary

    @staticmethod
    def _load_command_handlers(globals_: "Globals") -> dict[str, CommandHandler]:
        command_handlers: Final = parse_commands(CONFIG.commands_file)
        # Provide builtin commands:
        command_handlers["add-command"] = Globals.CommandAdder(globals_)
        command_handlers["edit-command"] = Globals.CommandChanger(globals_)
        command_handlers["delete-command"] = Globals.CommandDeleter(globals_)
        return command_handlers

    @staticmethod
    def _load_broadcasters() -> list[Broadcaster]:
        return parse_broadcasters(CONFIG.broadcasts_file)

    @staticmethod
    def _load_dictionary() -> Dictionary:
        return Dictionary(CONFIG.dictionary_file)

    @final
    class CommandAdder(CommandHandler):
        def __init__(self, globals_: "Globals") -> None:
            self._globals = globals_

        @override
        async def handle_command(self, chat_command: ChatCommand) -> Optional[list[ChatResponse]]:
            if len(chat_command.arguments) < 2:
                return [
                    ChatResponse(
                        text='Usage: /add-command <name> "<response>" [parameters...]',
                    )
                ]
            name: Final = chat_command.arguments[0].lstrip("!")
            if not Globals.CommandAdder._add_command(chat_command):
                return [
                    ChatResponse(
                        text=f"Command !{name} already exists.",
                    )
                ]
            self._globals._command_handlers = Globals._load_command_handlers(self._globals)
            return [
                ChatResponse(
                    text=f"Successfully added command !{name}.",
                )
            ]

        @property
        def min_required_permission_level(self) -> PermissionLevel:
            return PermissionLevel.MODERATOR

        @staticmethod
        def _add_command(chat_command: ChatCommand) -> bool:
            model: Final = CommandsModel.model_validate_json(
                CONFIG.commands_file.read_text(encoding="utf-8"),
            )
            name: Final = chat_command.arguments[0].lstrip("!")
            if name.lstrip("!") in (command.name for command in model.commands):
                return False
            if len(chat_command.arguments) == 1:
                model.commands.append(
                    StaticResponseCommandModel(
                        type="static",
                        name=name.lstrip("!"),
                        response=chat_command.arguments[0],
                    )
                )
            else:
                parameters: Final = chat_command.arguments[2:]
                model.commands.append(
                    ParameterizedResponseCommandModel(
                        type="parameterized",
                        name=name.lstrip("!"),
                        parameters=parameters,
                        response=chat_command.arguments[1],
                    )
                )
            CONFIG.commands_file.write_text(
                model.model_dump_json(indent=2),
                encoding="utf-8",
            )
            return True

    @final
    class CommandChanger(CommandHandler):
        def __init__(self, globals_: "Globals") -> None:
            self._globals = globals_

        @override
        async def handle_command(self, chat_command: ChatCommand) -> Optional[list[ChatResponse]]:
            if len(chat_command.arguments) != 2:
                return [
                    ChatResponse(
                        text='Usage: /edit-command <name> "<response>"',
                    )
                ]
            name, response = chat_command.arguments
            if not Globals.CommandChanger._change_command(name, response):
                return [
                    ChatResponse(
                        text=f"Command !{name.lstrip('!')} does not exist.",
                    )
                ]
            self._globals._command_handlers = Globals._load_command_handlers(self._globals)
            return [
                ChatResponse(
                    text=f"Successfully changed command !{name.lstrip('!')}.",
                )
            ]

        @property
        def min_required_permission_level(self) -> PermissionLevel:
            return PermissionLevel.MODERATOR

        @staticmethod
        def _change_command(name: str, response: str) -> bool:
            model: Final = CommandsModel.model_validate_json(
                CONFIG.commands_file.read_text(encoding="utf-8"),
            )
            for command in model.commands:
                if command.name == name.lstrip("!"):
                    command.response = response
                    CONFIG.commands_file.write_text(
                        model.model_dump_json(indent=2),
                        encoding="utf-8",
                    )
                    return True
            return False

    @final
    class CommandDeleter(CommandHandler):
        def __init__(self, globals_: "Globals") -> None:
            self._globals = globals_

        @override
        async def handle_command(self, chat_command: ChatCommand) -> Optional[list[ChatResponse]]:
            if len(chat_command.arguments) != 1:
                return [
                    ChatResponse(
                        text="Usage: /delete-command <name>",
                    )
                ]
            name = chat_command.arguments[0]
            if not Globals.CommandDeleter._delete_command(name):
                return [
                    ChatResponse(
                        text=f"Command !{name.lstrip('!')} does not exist.",
                    )
                ]
            self._globals._command_handlers = Globals._load_command_handlers(self._globals)
            return [
                ChatResponse(
                    text=f"Successfully deleted command !{name.lstrip('!')}.",
                )
            ]

        @property
        def min_required_permission_level(self) -> PermissionLevel:
            return PermissionLevel.MODERATOR

        @staticmethod
        def _delete_command(name: str) -> bool:
            model: Final = CommandsModel.model_validate_json(
                CONFIG.commands_file.read_text(encoding="utf-8"),
            )
            for command in model.commands:
                if command.name == name.lstrip("!"):
                    model.commands.remove(command)
                    CONFIG.commands_file.write_text(
                        model.model_dump_json(indent=2),
                        encoding="utf-8",
                    )
                    return True
            return False

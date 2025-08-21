import logging
from collections.abc import Callable
from pathlib import Path
from typing import Final
from typing import Optional
from typing import final
from typing import override

from chatbot2k.app_state import AppState
from chatbot2k.command_handlers.command_handler import CommandHandler
from chatbot2k.models.command_model import CommandModel
from chatbot2k.models.commands import CommandsModel
from chatbot2k.models.parameterized_response_command import ParameterizedResponseCommandModel
from chatbot2k.models.soundboard_command import SoundboardCommandModel
from chatbot2k.models.static_response_command import StaticResponseCommandModel
from chatbot2k.translations_manager import TranslationKey
from chatbot2k.types.chat_command import ChatCommand
from chatbot2k.types.chat_response import ChatResponse
from chatbot2k.types.permission_level import PermissionLevel


@final
class CommandManagementCommand(CommandHandler):
    COMMAND_NAME = "command"
    _ADD_SUBCOMMAND = "add"
    _ADD_CLIP_SUBCOMMAND = "add-clip"
    _UPDATE_SUBCOMMAND = "update"
    _REMOVE_SUBCOMMAND = "remove"

    def __init__(self, app_state: AppState, on_commands_changed: Callable[[], None]) -> None:
        super().__init__(app_state, name=CommandManagementCommand.COMMAND_NAME)
        self._on_commands_changed: Final = on_commands_changed

    @override
    async def handle_command(self, chat_command: ChatCommand) -> Optional[list[ChatResponse]]:
        argc: Final = len(chat_command.arguments)  # The subcommand (e.g. "add") is included in this count!
        match chat_command.arguments[0].lower():
            case CommandManagementCommand._ADD_SUBCOMMAND if argc >= 3:
                success, response = CommandManagementCommand._add_or_update_command(
                    self._app_state,
                    chat_command,
                    is_update=False,
                )
            case CommandManagementCommand._ADD_CLIP_SUBCOMMAND if argc >= 3:
                success, response = CommandManagementCommand._add_clip_command(
                    self._app_state,
                    chat_command,
                )
            case CommandManagementCommand._UPDATE_SUBCOMMAND if argc >= 3:
                success, response = CommandManagementCommand._add_or_update_command(
                    self._app_state,
                    chat_command,
                    is_update=True,
                )
            case CommandManagementCommand._REMOVE_SUBCOMMAND if argc >= 2:
                success, response = CommandManagementCommand._remove_command(
                    self._app_state,
                    chat_command,
                )
            case _:
                return None
        if success:
            self._on_commands_changed()
        return [
            ChatResponse(
                text=response,
                chat_message=chat_command.source_message,
            )
        ]

    @override
    @property
    def min_required_permission_level(self) -> PermissionLevel:
        return PermissionLevel.MODERATOR

    @override
    @property
    def usage(self) -> str:
        return "!command [add|add-clip|update|remove] <parameters>..."

    @override
    @property
    def description(self) -> str:
        return (
            "Manage custom commands. Use `!command add` to add a new command, `!command add-clip` to add "
            + "a soundboard command, `!command update` to update an existing command, and `!command remove` "
            + "to delete a command."
        )

    @staticmethod
    def _load_command_handlers(
        *,
        commands_file: Path,
        create_if_missing: bool,
    ) -> list[CommandModel]:
        if create_if_missing and not commands_file.exists():
            logging.info(f"Commands file {commands_file} does not exist, creating a new one.")
            commands_file.parent.mkdir(parents=True, exist_ok=True)
            CommandManagementCommand._save_commands(commands_file=commands_file, commands=[])
        file_contents: Final = commands_file.read_text(encoding="utf-8")
        return CommandsModel.model_validate_json(file_contents).commands

    @staticmethod
    def _save_commands(
        *,
        commands_file: Path,
        commands: list[CommandModel],
    ) -> None:
        model: Final = CommandsModel(commands=sorted(commands, key=lambda c: c.name))
        commands_file.write_text(
            model.model_dump_json(indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _add_or_update_command(
        app_state: AppState,
        chat_command: ChatCommand,
        *,
        is_update: bool,
    ) -> tuple[bool, str]:
        name: Final = chat_command.arguments[1].lstrip("!")

        # We need a special check for *all* registered command handlers, because there are
        # also builtin ones that are not included in the commands file. Those can neither be
        # added nor updated, so we return an error message.
        if name in app_state.command_handlers:
            return (
                False,
                app_state.translations_manager.get_translation(TranslationKey.COMMAND_ALREADY_EXISTS),
            )

        commands: Final = CommandManagementCommand._load_command_handlers(
            commands_file=app_state.config.commands_file,
            create_if_missing=False,
        )
        existing_command: Final = next((command for command in commands if command.name == name), None)
        if existing_command is None and is_update:
            return (
                False,
                app_state.translations_manager.get_translation(TranslationKey.COMMAND_TO_UPDATE_NOT_FOUND),
            )
        if existing_command is not None and not is_update:
            return (
                False,
                app_state.translations_manager.get_translation(TranslationKey.COMMAND_ALREADY_EXISTS),
            )
        if existing_command is not None:
            commands.remove(existing_command)

        if len(chat_command.arguments) == 3:
            commands.append(
                StaticResponseCommandModel(
                    type="static",
                    name=name.lstrip("!"),
                    response=chat_command.arguments[2],
                )
            )
        else:
            parameters: Final = chat_command.arguments[3:]
            commands.append(
                ParameterizedResponseCommandModel(
                    type="parameterized",
                    name=name.lstrip("!"),
                    parameters=parameters,
                    response=chat_command.arguments[2],
                )
            )
        CommandManagementCommand._save_commands(
            commands_file=app_state.config.commands_file,
            commands=commands,
        )
        return (
            True,
            app_state.translations_manager.get_translation(
                TranslationKey.COMMAND_UPDATED if is_update else TranslationKey.COMMAND_ADDED
            ),
        )

    @staticmethod
    def _add_clip_command(
        app_state: AppState,
        chat_command: ChatCommand,
    ) -> tuple[bool, str]:
        name: Final = chat_command.arguments[1].lstrip("!")

        if name in app_state.command_handlers:
            return (
                False,
                app_state.translations_manager.get_translation(TranslationKey.COMMAND_ALREADY_EXISTS),
            )

        commands: Final = CommandManagementCommand._load_command_handlers(
            commands_file=app_state.config.commands_file,
            create_if_missing=False,
        )
        commands.append(
            SoundboardCommandModel(
                type="soundboard",
                name=name.lstrip("!"),
                clip_url=chat_command.arguments[2],
            )
        )
        CommandManagementCommand._save_commands(
            commands_file=app_state.config.commands_file,
            commands=commands,
        )
        return (
            True,
            app_state.translations_manager.get_translation(TranslationKey.COMMAND_ADDED),
        )

    @staticmethod
    def _remove_command(app_state: AppState, chat_command: ChatCommand) -> tuple[bool, str]:
        commands: Final = CommandManagementCommand._load_command_handlers(
            commands_file=app_state.config.commands_file,
            create_if_missing=False,
        )
        name: Final = chat_command.arguments[1].lstrip("!")
        for command in commands:
            if command.name == name:
                commands.remove(command)
                CommandManagementCommand._save_commands(
                    commands_file=app_state.config.commands_file,
                    commands=commands,
                )
                return (
                    True,
                    app_state.translations_manager.get_translation(TranslationKey.COMMAND_REMOVED),
                )
        # If no command has been found, it could still be the case that this is a builtin command.
        # For that case, we want to provide a different error message.
        if name in app_state.command_handlers:
            return (
                False,
                app_state.translations_manager.get_translation(TranslationKey.BUILTIN_COMMAND_CANNOT_BE_DELETED),
            )
        return (
            False,
            app_state.translations_manager.get_translation(TranslationKey.COMMAND_TO_DELETE_NOT_FOUND),
        )

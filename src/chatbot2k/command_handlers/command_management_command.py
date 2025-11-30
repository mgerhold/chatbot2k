import asyncio
from collections.abc import Callable
from typing import Final
from typing import NamedTuple
from typing import Optional
from typing import final
from typing import override

import requests

from chatbot2k.app_state import AppState
from chatbot2k.command_handlers.command_handler import CommandHandler
from chatbot2k.database.engine import ScriptStoreData
from chatbot2k.scripting_engine.lexer import Lexer
from chatbot2k.scripting_engine.parser import Parser
from chatbot2k.scripting_engine.stores import StoreKey
from chatbot2k.scripting_engine.types.expressions import ExecutionContext
from chatbot2k.translation_key import TranslationKey
from chatbot2k.types.chat_command import ChatCommand
from chatbot2k.types.chat_response import ChatResponse
from chatbot2k.types.permission_level import PermissionLevel


@final
class _SerializedScript(NamedTuple):
    script_json: str
    store_data: list[ScriptStoreData]


type _ErrorMessage = str


@final
class CommandManagementCommand(CommandHandler):
    COMMAND_NAME = "command"
    _ADD_SUBCOMMAND = "add"
    _ADD_CLIP_SUBCOMMAND = "add-clip"
    _ADD_SCRIPT_SUBCOMMAND = "add-script"
    _UPDATE_SUBCOMMAND = "update"
    _REMOVE_SUBCOMMAND = "remove"

    def __init__(self, app_state: AppState, on_commands_changed: Callable[[], None]) -> None:
        super().__init__(app_state, name=CommandManagementCommand.COMMAND_NAME)
        self._on_commands_changed: Final = on_commands_changed

    @override
    async def handle_command(self, chat_command: ChatCommand) -> Optional[list[ChatResponse]]:
        argc: Final = len(chat_command.arguments)  # The subcommand (e.g. "add") is included in this count!
        if argc < 1:
            return None
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
            case CommandManagementCommand._ADD_SCRIPT_SUBCOMMAND if argc >= 3:
                success, response = await CommandManagementCommand._add_script_command(
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

    @property
    @override
    def min_required_permission_level(self) -> PermissionLevel:
        return PermissionLevel.MODERATOR

    @property
    @override
    def usage(self) -> str:
        return "!command [add|add-clip|add-script|update|remove] <parameters>..."

    @property
    @override
    def description(self) -> str:
        return (
            "Manage custom commands. Use `!command add` to add a new command, `!command add-clip` to add "
            + "a soundboard command, `!command add-script` to add a script command, `!command update` to "
            + "update an existing command, and `!command remove` to delete a command."
        )

    @staticmethod
    def _add_or_update_command(
        app_state: AppState,
        chat_command: ChatCommand,
        *,
        is_update: bool,
    ) -> tuple[bool, str]:
        name: Final = chat_command.arguments[1].lstrip("!")

        soundboard_commands: Final = app_state.database.get_soundboard_commands()
        if name.lower() in (command.name.lower() for command in soundboard_commands):
            return (
                False,
                app_state.translations_manager.get_translation(TranslationKey.CANNOT_ADD_OR_UPDATE_SOUNDBOARD_COMMAND),
            )

        scripts: Final = app_state.database.get_scripts()
        if name.lower() in (script.command.lower() for script in scripts):
            return (
                False,
                app_state.translations_manager.get_translation(TranslationKey.CANNOT_ADD_OR_UPDATE_SCRIPT_COMMAND),
            )

        static_commands: Final = app_state.database.get_static_commands()
        parameterized_commands: Final = app_state.database.get_parameterized_commands()
        commands: Final = static_commands + parameterized_commands

        existing_command: Final = next((command for command in commands if command.name.lower() == name.lower()), None)

        # We need a special check for *all* registered command handlers, because there are
        # also builtin ones that are not included in the database. Those can neither be
        # added nor updated, so we return an error message.
        if existing_command is None and name.lower() in (command.lower() for command in app_state.command_handlers):
            return (
                False,
                app_state.translations_manager.get_translation(TranslationKey.BUILTIN_COMMAND_CANNOT_BE_CHANGED),
            )

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
            app_state.database.remove_command_case_insensitive(name=existing_command.name)

        if len(chat_command.arguments) == 3:
            app_state.database.add_static_command(
                name=name,
                response=chat_command.arguments[2],
            )
        else:
            parameters: Final = chat_command.arguments[3:]
            app_state.database.add_parameterized_command(
                name=name,
                response=chat_command.arguments[2],
                parameters=parameters,
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

        if name.lower() in (command.lower() for command in app_state.command_handlers):
            return (
                False,
                app_state.translations_manager.get_translation(TranslationKey.COMMAND_ALREADY_EXISTS),
            )

        app_state.database.add_soundboard_command(
            name=name,
            clip_url=chat_command.arguments[2],
        )

        return (
            True,
            app_state.translations_manager.get_translation(TranslationKey.COMMAND_ADDED),
        )

    @staticmethod
    async def _add_script_command(
        app_state: AppState,
        chat_command: ChatCommand,
    ) -> tuple[bool, str]:
        """Add a script command by parsing the source code and storing it in the database.

        Args:
            app_state: Application state containing database and other services
            chat_command: The chat command containing arguments: [subcommand, name, source_code]

        Returns:
            Tuple of (success: bool, response_message: str)
        """
        name: Final = chat_command.arguments[1].lstrip("!")
        source_code: Final = chat_command.arguments[2]

        # Check if command already exists.
        if name.lower() in (command.lower() for command in app_state.command_handlers):
            return (
                False,
                app_state.translations_manager.get_translation(TranslationKey.COMMAND_ALREADY_EXISTS),
            )

        serialized_script = await CommandManagementCommand._try_serialize_script(app_state, name, source_code)

        if isinstance(serialized_script, str):
            # Parsing did not work. Let's try to interpret the source code as a URL to a script file.
            try:
                response: Final = await asyncio.to_thread(requests.get, source_code)
            except Exception as e:
                return (
                    False,
                    f"Failed to fetch script from URL: {e}",
                )
            serialized_script = await CommandManagementCommand._try_serialize_script(app_state, name, response.text)

        match serialized_script:
            case str():
                return (
                    False,
                    serialized_script,
                )
            case _SerializedScript(script_json, store_data):
                # Add to database.
                app_state.database.add_script(
                    command=name,
                    source_code=source_code,
                    script_json=script_json,
                    stores=store_data,
                )

                return (
                    True,
                    app_state.translations_manager.get_translation(TranslationKey.COMMAND_ADDED),
                )

    @staticmethod
    async def _try_serialize_script(
        app_state: AppState,
        name: str,
        source_code: str,
    ) -> _SerializedScript | _ErrorMessage:
        try:
            # Tokenize the source code.
            lexer: Final = Lexer(source_code)
            tokens: Final = lexer.tokenize()

            # Parse the tokens.
            parser: Final = Parser(name, tokens)
            script: Final = parser.parse()

            # Evaluate store initial values.
            store_data: Final[list[ScriptStoreData]] = []

            async def _script_caller(script_name: str, *args: str) -> str:
                raise NotImplementedError

            execution_context: Final = ExecutionContext(
                app_state=app_state,
                call_stack=[script.name],
                stores={},
                parameters={},  # Empty dict because parameter definitions do not access values.
                variables={},  # Empty dict because variables cannot be defined before stores.
                call_script=_script_caller,
            )

            for store in script.stores:
                store_key = StoreKey(
                    script_name=script.name,
                    store_name=store.name,
                )
                # Evaluate the initial value expression.
                try:
                    value = await store.value.evaluate(execution_context)
                    execution_context.stores[store_key] = value

                    # Serialize to JSON.
                    store_json = store.model_dump_json()
                    value_json = value.model_dump_json()

                    store_data.append(
                        ScriptStoreData(
                            store_name=store.name,
                            store_json=store_json,
                            value_json=value_json,
                        )
                    )
                except Exception as e:
                    return f"Error evaluating store '{store.name}': {e}"

            return _SerializedScript(script.model_dump_json(), store_data)
        except Exception as e:
            # Catch lexer/parser errors and return a friendly message.
            return f"Script parsing error: {e}"

    @staticmethod
    def _remove_command(app_state: AppState, chat_command: ChatCommand) -> tuple[bool, str]:
        name: Final = chat_command.arguments[1].lstrip("!")
        was_removed: Final = app_state.database.remove_command_case_insensitive(name=name)
        if was_removed:
            return (
                True,
                app_state.translations_manager.get_translation(TranslationKey.COMMAND_REMOVED),
            )

        # If no command has been found, it could still be the case that this is a builtin command.
        # For that case, we want to provide a different error message.
        if name.lower() in (command.lower() for command in app_state.command_handlers):
            return (
                False,
                app_state.translations_manager.get_translation(TranslationKey.BUILTIN_COMMAND_CANNOT_BE_DELETED),
            )

        return (
            False,
            app_state.translations_manager.get_translation(TranslationKey.COMMAND_TO_DELETE_NOT_FOUND),
        )

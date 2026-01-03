import asyncio
import logging
from typing import Final
from typing import Optional
from typing import final
from typing import override

from chatbot2k.app_state import AppState
from chatbot2k.command_handlers.command_handler import CommandHandler
from chatbot2k.scripting_engine.database_persistent_store import DatabasePersistentStore
from chatbot2k.scripting_engine.types.ast import Script
from chatbot2k.scripting_engine.types.script_caller import ScriptCaller
from chatbot2k.types.chat_command import ChatCommand
from chatbot2k.types.chat_response import ChatResponse
from chatbot2k.types.configuration_setting_kind import ConfigurationSettingKind
from chatbot2k.types.permission_level import PermissionLevel

logger: Final = logging.getLogger(__name__)


@final
class ScriptCommandHandler(CommandHandler):
    """Command handler that executes a stored script."""

    def __init__(
        self,
        app_state: AppState,
        *,
        name: str,
        script_json: str,
        call_script: ScriptCaller,
    ) -> None:
        super().__init__(app_state, name=name)
        # Deserialize the script from JSON.
        self._script: Final = Script.model_validate_json(script_json)
        self._persistent_store: Final = DatabasePersistentStore(app_state.database)
        self._call_script: Final = call_script

    @override
    async def handle_command(self, chat_command: ChatCommand) -> Optional[list[ChatResponse]]:
        timeout_string: Final = self._app_state.database.retrieve_configuration_setting(
            ConfigurationSettingKind.SCRIPT_EXECUTION_TIMEOUT
        )
        if timeout_string is None or not timeout_string or not timeout_string.isdigit():
            raise AssertionError("Invalid script timeout configuration - this should never happen")
        timeout_seconds: Final = int(timeout_string)

        # Execute the script with a timeout to prevent abuse.
        start_time: Final = asyncio.get_event_loop().time()
        try:
            timeout_task: Final = asyncio.create_task(asyncio.sleep(timeout_seconds))
            execution_task: Final = asyncio.create_task(
                self._script.execute(
                    self._persistent_store,
                    chat_command.arguments,
                    self._call_script,
                    self._app_state,
                )
            )
            await asyncio.wait(
                (timeout_task, execution_task),
                return_when=asyncio.FIRST_COMPLETED,
            )
            if timeout_task.done():
                execution_task.cancel()
                return [
                    ChatResponse(
                        text=(f"Script '!{self._name}' execution timed out " + f"(exceeded {timeout_seconds}s)"),
                        chat_message=chat_command.source_message,
                    )
                ]
            assert execution_task.done()
            output: Final = execution_task.result()
        except Exception as e:
            return [
                ChatResponse(
                    text=f"An error occurred while executing the script '!{self._name}': {e}",
                    chat_message=chat_command.source_message,
                )
            ]

        # If the script produced output, return it as a chat response.
        if output is None:
            return None

        end_time: Final = asyncio.get_event_loop().time()
        logger.info(f"Executed script '!{self._name}' in {(end_time - start_time) * 1000.0:.4f} ms")

        return [
            ChatResponse(
                text=output,
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
        return f"Executes the '{self._name}' script"

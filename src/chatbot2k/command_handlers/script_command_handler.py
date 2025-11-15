import asyncio
from typing import Final
from typing import Optional
from typing import final
from typing import override

from chatbot2k.app_state import AppState
from chatbot2k.command_handlers.command_handler import CommandHandler
from chatbot2k.scripting_engine.database_persistent_store import DatabasePersistentStore
from chatbot2k.scripting_engine.types.ast import Script
from chatbot2k.types.chat_command import ChatCommand
from chatbot2k.types.chat_response import ChatResponse
from chatbot2k.types.permission_level import PermissionLevel


@final
class ScriptCommandHandler(CommandHandler):
    """Command handler that executes a stored script."""

    _EXECUTION_TIMEOUT_SECONDS: Final = 0.1

    def __init__(
        self,
        app_state: AppState,
        *,
        name: str,
        script_json: str,
    ) -> None:
        super().__init__(app_state, name=name)
        # Deserialize the script from JSON.
        self._script: Final = Script.model_validate_json(script_json)
        self._persistent_store: Final = DatabasePersistentStore(app_state.database)

    @override
    async def handle_command(self, chat_command: ChatCommand) -> Optional[list[ChatResponse]]:
        # Execute the script with a timeout to prevent abuse.
        try:
            output: Final = await asyncio.wait_for(
                asyncio.to_thread(self._script.execute, self._persistent_store, chat_command.arguments),
                timeout=self._EXECUTION_TIMEOUT_SECONDS,
            )
        except TimeoutError:
            return [
                ChatResponse(
                    text=f"Script '!{self._name}' execution timed out (exceeded {self._EXECUTION_TIMEOUT_SECONDS}s)",
                    chat_message=chat_command.source_message,
                )
            ]
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

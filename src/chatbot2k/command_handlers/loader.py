import logging
from typing import Final

from chatbot2k.app_state import AppState
from chatbot2k.command_handlers.clip_handler import ClipHandler
from chatbot2k.command_handlers.command_handler import CommandHandler
from chatbot2k.command_handlers.parameterized_response_command import ParameterizedResponseCommand
from chatbot2k.command_handlers.script_command_handler import ScriptCommandHandler
from chatbot2k.command_handlers.static_response_command import StaticResponseCommand
from chatbot2k.scripting_engine.database_persistent_store import DatabasePersistentStore
from chatbot2k.scripting_engine.parser import Script
from chatbot2k.scripting_engine.types.execution_error import ExecutionError


def load_commands(app_state: AppState) -> dict[str, CommandHandler]:
    result: dict[str, CommandHandler] = {}
    for static_command in app_state.database.get_static_commands():
        assert static_command.name.lower() not in (name.lower() for name in result)
        logging.info(f"Loaded static command: !{static_command.name}")
        result[static_command.name] = StaticResponseCommand(
            app_state=app_state,
            name=static_command.name,
            response=static_command.response,
        )

    for parameterized_command in app_state.database.get_parameterized_commands():
        assert parameterized_command.name.lower() not in (name.lower() for name in result)
        logging.info(
            f"Loaded parameterized command: !{parameterized_command.name} "
            + f"{' '.join(f'{parameter}' for parameter in parameterized_command.parameters)}"
        )
        result[parameterized_command.name] = ParameterizedResponseCommand(
            app_state=app_state,
            name=parameterized_command.name,
            parameters=parameterized_command.parameters,
            format_string=parameterized_command.response,
        )

    for soundboard_command in app_state.database.get_soundboard_commands():
        assert soundboard_command.name.lower() not in (name.lower() for name in result)
        logging.info(f"Loaded soundboard command: !{soundboard_command.name}")
        result[soundboard_command.name] = ClipHandler(
            app_state=app_state,
            name=soundboard_command.name,
            clip_url=soundboard_command.clip_url,
        )

    database_persistent_store: Final = DatabasePersistentStore(app_state.database)

    async def _call_script(script_name: str, *args: str) -> str:
        script_name = script_name.removeprefix("!").lower()
        database_script: Final = app_state.database.get_script(script_name)
        if database_script is None:
            msg = f"Script '{script_name}' not found."
            raise ExecutionError(msg)
        script: Final = Script.model_validate_json(database_script.script_json)
        # Note: `Script.execute()` performs an arity check.
        script_output: Final = await script.execute(
            persistent_store=database_persistent_store,
            arguments=list(args),
            call_script=_call_script,
        )
        if script_output is None:
            msg = f"Script '{script_name}' did not return any output."
            raise ExecutionError(msg)
        return script_output

    for script in app_state.database.get_scripts():
        assert script.command.lower() not in (name.lower() for name in result)
        logging.info(f"Loaded script command: !{script.command}")
        result[script.command] = ScriptCommandHandler(
            app_state=app_state,
            name=script.command,
            script_json=script.script_json,
            call_script=_call_script,
        )

    return result

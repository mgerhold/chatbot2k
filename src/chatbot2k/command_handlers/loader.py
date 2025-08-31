import logging

from chatbot2k.app_state import AppState
from chatbot2k.command_handlers.clip_handler import ClipHandler
from chatbot2k.command_handlers.command_handler import CommandHandler
from chatbot2k.command_handlers.parameterized_response_command import ParameterizedResponseCommand
from chatbot2k.command_handlers.static_response_command import StaticResponseCommand


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

    return result

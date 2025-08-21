import logging
from typing import Final

from pydantic import ValidationError

from chatbot2k.app_state import AppState
from chatbot2k.command_handlers.clip_handler import ClipHandler
from chatbot2k.command_handlers.command_handler import CommandHandler
from chatbot2k.command_handlers.parameterized_response_command import ParameterizedResponseCommand
from chatbot2k.command_handlers.static_response_command import StaticResponseCommand
from chatbot2k.models.commands import CommandsModel
from chatbot2k.models.parameterized_response_command import ParameterizedResponseCommandModel
from chatbot2k.models.soundboard_command import SoundboardCommandModel
from chatbot2k.models.static_response_command import StaticResponseCommandModel


def parse_commands(app_state: AppState) -> dict[str, CommandHandler]:
    commands_file: Final = app_state.config.commands_file
    if not commands_file.exists():
        raise FileNotFoundError(f"Commands file not found: {commands_file}")
    try:
        contents: Final = commands_file.read_text(encoding="utf-8")
    except Exception as e:
        msg: Final = f"Error reading commands file: {commands_file}. Error: {e}"
        raise RuntimeError(msg) from e

    try:
        commands: Final = CommandsModel.model_validate_json(contents)
    except ValidationError as e:
        msg: Final = f"Error validating commands file: {commands_file}. Error: {e}"
        raise RuntimeError(msg) from e

    result: dict[str, CommandHandler] = {}
    for command in commands.commands:
        match command:
            case StaticResponseCommandModel():
                logging.info(
                    f"Parsed `StaticResponseCommand` with name '!{command.name}'"
                    + f" that responds with '{command.response}'"
                )
                result[command.name] = StaticResponseCommand(
                    app_state=app_state,
                    name=command.name,
                    response=command.response,
                )
            case ParameterizedResponseCommandModel():
                logging.info(
                    f"Parser `ParameterizedResponseCommandModel` with name '!{command.name}'"
                    + f" that has parameters `{command.parameters}` and responds with '{command.response}'"
                )
                result[command.name] = ParameterizedResponseCommand(
                    app_state=app_state,
                    name=command.name,
                    parameters=command.parameters,
                    format_string=command.response,
                )
            case SoundboardCommandModel():
                logging.info(
                    f"Parsed `SoundboardCommand` with name '!{command.name}'" + f" that plays clip '{command.clip_url}'"
                )
                result[command.name] = ClipHandler(
                    app_state=app_state,
                    name=command.name,
                    clip_url=command.clip_url,
                )
            case _:
                raise NotImplementedError
    return result

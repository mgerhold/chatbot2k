import json
import logging
from typing import Final
from typing import final
from typing import override

from chatbot2k.app_state import AppState
from chatbot2k.broadcasters.broadcaster import Broadcaster
from chatbot2k.broadcasters.parser import parse_broadcasters
from chatbot2k.command_handlers.command_handler import CommandHandler
from chatbot2k.command_handlers.command_management_command import CommandManagementCommand
from chatbot2k.command_handlers.parser import parse_commands
from chatbot2k.config import CONFIG
from chatbot2k.dictionary import Dictionary
from chatbot2k.models.broadcasts import BroadcastsModel
from chatbot2k.models.commands import CommandsModel
from chatbot2k.models.static_response_command import StaticResponseCommandModel
from chatbot2k.translations_manager import TranslationsManager


@final
class Globals(AppState):
    def __init__(self) -> None:
        self._command_handlers = self._reload_command_handlers(create_if_missing=True)
        self._broadcasters = Globals._load_broadcasters(create_if_missing=True)
        self._dictionary = Globals._load_dictionary(create_if_missing=True)
        self._translations_manager = TranslationsManager(create_if_missing=True)

    @override
    @property
    def command_handlers(self) -> dict[str, CommandHandler]:
        return self._command_handlers

    @override
    @property
    def broadcasters(self) -> list[Broadcaster]:
        return self._broadcasters

    @override
    @property
    def dictionary(self) -> Dictionary:
        return self._dictionary

    @override
    @property
    def translations_manager(self) -> TranslationsManager:
        return self._translations_manager

    def _on_commands_changed(self) -> None:
        self._command_handlers = self._reload_command_handlers(create_if_missing=False)

    def _reload_command_handlers(
        self,
        *,
        create_if_missing: bool,
    ) -> dict[str, CommandHandler]:
        if create_if_missing and not CONFIG.commands_file.exists():
            logging.info(f"Commands file {CONFIG.commands_file} does not exist, creating a new one.")
            CONFIG.commands_file.parent.mkdir(parents=True, exist_ok=True)
            CONFIG.commands_file.write_text(
                CommandsModel(
                    commands=[
                        StaticResponseCommandModel(
                            name="hello",
                            response="Hello, world!",
                        ),
                    ]
                ).model_dump_json(indent=2),
                encoding="utf-8",
            )
        command_handlers: Final = parse_commands(self, CONFIG.commands_file)
        command_handlers["command"] = CommandManagementCommand(
            self,
            lambda: self._on_commands_changed(),
        )
        return command_handlers

    @staticmethod
    def _load_broadcasters(*, create_if_missing: bool) -> list[Broadcaster]:
        if create_if_missing and not CONFIG.broadcasts_file.exists():
            logging.info(f"Broadcasts file {CONFIG.broadcasts_file} does not exist, creating a new one.")
            CONFIG.broadcasts_file.parent.mkdir(parents=True, exist_ok=True)
            CONFIG.broadcasts_file.write_text(
                BroadcastsModel(broadcasts=[]).model_dump_json(indent=2),
                encoding="utf-8",
            )
        return parse_broadcasters(CONFIG.broadcasts_file)

    @staticmethod
    def _load_dictionary(*, create_if_missing: bool) -> Dictionary:
        if create_if_missing and not CONFIG.dictionary_file.exists():
            logging.info(f"Dictionary file {CONFIG.dictionary_file} does not exist, creating a new one.")
            CONFIG.dictionary_file.parent.mkdir(parents=True, exist_ok=True)
            CONFIG.dictionary_file.write_text(json.dumps([]))
        return Dictionary(CONFIG.dictionary_file)

import json
import logging
from pathlib import Path
from typing import Final
from typing import final
from typing import override

from chatbot2k.app_state import AppState
from chatbot2k.broadcasters.broadcaster import Broadcaster
from chatbot2k.broadcasters.parser import parse_broadcasters
from chatbot2k.command_handlers.command_handler import CommandHandler
from chatbot2k.command_handlers.command_management_command import CommandManagementCommand
from chatbot2k.command_handlers.dictionary_handler import DictionaryHandler
from chatbot2k.command_handlers.parser import parse_commands
from chatbot2k.config import Config
from chatbot2k.constants import load_constants
from chatbot2k.dictionary import Dictionary
from chatbot2k.models.broadcasts import BroadcastsModel
from chatbot2k.models.commands import CommandsModel
from chatbot2k.models.static_response_command import StaticResponseCommandModel
from chatbot2k.translations_manager import TranslationsManager


@final
class Globals(AppState):
    def __init__(self) -> None:
        self._config: Final = Config()
        self._constants: Final = load_constants(
            constants_file=self.config.constants_file,
            create_if_missing=True,
        )
        self._command_handlers = self._reload_command_handlers(create_if_missing=True)
        self._broadcasters = Globals._load_broadcasters(
            broadcasts_file=self.config.broadcasts_file,
            create_if_missing=True,
            app_state=self,
        )
        self._dictionary = Globals._load_dictionary(
            dictionary_file=self.config.dictionary_file,
            create_if_missing=True,
        )
        self._translations_manager = TranslationsManager(config=self.config, create_if_missing=True)

    @override
    @property
    def config(self) -> Config:
        return self._config

    @override
    @property
    def constants(self) -> dict[str, str]:
        return self._constants

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
        if create_if_missing and not self.config.commands_file.exists():
            logging.info(f"Commands file {self.config.commands_file} does not exist, creating a new one.")
            self.config.commands_file.parent.mkdir(parents=True, exist_ok=True)
            self.config.commands_file.write_text(
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
        command_handlers: Final = parse_commands(self, self.config.commands_file)
        command_handlers[CommandManagementCommand.COMMAND_NAME] = CommandManagementCommand(
            self,
            lambda: self._on_commands_changed(),
        )
        command_handlers[DictionaryHandler.COMMAND_NAME] = DictionaryHandler(self)
        return command_handlers

    @staticmethod
    def _load_broadcasters(
        *,
        broadcasts_file: Path,
        create_if_missing: bool,
        app_state: AppState,
    ) -> list[Broadcaster]:
        if create_if_missing and not broadcasts_file.exists():
            logging.info(f"Broadcasts file {broadcasts_file} does not exist, creating a new one.")
            broadcasts_file.parent.mkdir(parents=True, exist_ok=True)
            broadcasts_file.write_text(
                BroadcastsModel(broadcasts=[]).model_dump_json(indent=2),
                encoding="utf-8",
            )
        return parse_broadcasters(broadcasts_file, app_state)

    @staticmethod
    def _load_dictionary(*, dictionary_file: Path, create_if_missing: bool) -> Dictionary:
        if create_if_missing and not dictionary_file.exists():
            logging.info(f"Dictionary file {dictionary_file} does not exist, creating a new one.")
            dictionary_file.parent.mkdir(parents=True, exist_ok=True)
            dictionary_file.write_text(json.dumps([]))
        return Dictionary(dictionary_file)

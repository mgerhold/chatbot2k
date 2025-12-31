import asyncio
from typing import Final
from typing import final
from typing import override
from uuid import UUID

from chatbot2k.app_state import AppState
from chatbot2k.broadcasters.broadcaster import Broadcaster
from chatbot2k.broadcasters.parser import parse_broadcasters
from chatbot2k.command_handlers.command_handler import CommandHandler
from chatbot2k.command_handlers.command_management_command import CommandManagementCommand
from chatbot2k.command_handlers.dictionary_handler import DictionaryHandler
from chatbot2k.command_handlers.giveaway_enter_handler import GiveawayEnterCommand
from chatbot2k.command_handlers.giveaway_handler import GiveawayCommand
from chatbot2k.command_handlers.loader import load_commands
from chatbot2k.command_handlers.soundboard_handlers import SoundboardHandler
from chatbot2k.config import Config
from chatbot2k.database.engine import Database
from chatbot2k.dictionary import Dictionary
from chatbot2k.translations_manager import TranslationsManager
from chatbot2k.types.commands import Command


@final
class Globals(AppState):
    def __init__(self) -> None:
        self._is_soundboard_enabled = True
        self._config: Final = Config()
        self._database: Final = Database(self.config.database_file, echo=False)
        self._monitored_channels_changed: Final = asyncio.Event()
        self._soundboard_clips_url_queues: Final[dict[UUID, asyncio.Queue[str]]] = {}
        self._command_handlers = self._reload_command_handlers()
        self._broadcasters: Final = Globals._load_broadcasters(self)
        self._dictionary: Final = Globals._load_dictionary(self.database)
        self._translations_manager: Final = TranslationsManager(self.database)
        self._command_queue: Final = asyncio.Queue[Command]()

    @property
    @override
    def config(self) -> Config:
        return self._config

    @property
    @override
    def database(self) -> Database:
        return self._database

    @property
    @override
    def command_handlers(self) -> dict[str, CommandHandler]:
        return self._command_handlers

    @property
    @override
    def broadcasters(self) -> list[Broadcaster]:
        return self._broadcasters

    @property
    @override
    def dictionary(self) -> Dictionary:
        return self._dictionary

    @property
    @override
    def translations_manager(self) -> TranslationsManager:
        return self._translations_manager

    @property
    @override
    def monitored_channels_changed(self) -> asyncio.Event:
        return self._monitored_channels_changed

    @property
    @override
    def soundboard_clips_url_queues(self) -> dict[UUID, asyncio.Queue[str]]:
        return self._soundboard_clips_url_queues

    @property
    @override
    def is_soundboard_enabled(self) -> bool:
        return self._is_soundboard_enabled

    @is_soundboard_enabled.setter
    @override
    def is_soundboard_enabled(self, value: bool) -> None:
        self._is_soundboard_enabled = value

    @property
    @override
    def command_queue(self) -> asyncio.Queue[Command]:
        return self._command_queue

    def _on_commands_changed(self) -> None:
        self._command_handlers = self._reload_command_handlers()

    def _reload_command_handlers(self) -> dict[str, CommandHandler]:
        command_handlers: Final = load_commands(self)
        command_handlers[CommandManagementCommand.COMMAND_NAME] = CommandManagementCommand(
            self,
            lambda: self._on_commands_changed(),
        )
        command_handlers[GiveawayCommand.COMMAND_NAME] = GiveawayCommand(self)
        command_handlers[GiveawayEnterCommand.COMMAND_NAME] = GiveawayEnterCommand(self)
        command_handlers[DictionaryHandler.COMMAND_NAME] = DictionaryHandler(self)
        command_handlers[SoundboardHandler.COMMAND_NAME] = SoundboardHandler(self)
        return command_handlers

    @staticmethod
    def _load_broadcasters(app_state: AppState) -> list[Broadcaster]:
        return parse_broadcasters(app_state)

    @staticmethod
    def _load_dictionary(database: Database) -> Dictionary:
        return Dictionary(database)

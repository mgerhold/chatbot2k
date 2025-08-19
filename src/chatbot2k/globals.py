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
from chatbot2k.translations_manager import TranslationsManager


@final
class Globals(AppState):
    def __init__(self) -> None:
        self._command_handlers = self._reload_command_handlers()
        self._broadcasters = Globals._load_broadcasters()
        self._dictionary = Globals._load_dictionary()
        self._translations_manager = TranslationsManager()

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
        self._command_handlers = self._reload_command_handlers()

    def _reload_command_handlers(self) -> dict[str, CommandHandler]:
        command_handlers: Final = parse_commands(self, CONFIG.commands_file)
        command_handlers["command"] = CommandManagementCommand(
            self,
            lambda: self._on_commands_changed(),
        )
        return command_handlers

    @staticmethod
    def _load_broadcasters() -> list[Broadcaster]:
        return parse_broadcasters(CONFIG.broadcasts_file)

    @staticmethod
    def _load_dictionary() -> Dictionary:
        return Dictionary(CONFIG.dictionary_file)

import asyncio
from abc import ABC
from abc import abstractmethod
from typing import TYPE_CHECKING

from chatbot2k.broadcasters.broadcaster import Broadcaster
from chatbot2k.config import Config
from chatbot2k.dictionary import Dictionary
from chatbot2k.translations_manager import TranslationsManager

if TYPE_CHECKING:
    # We have to avoid circular imports, so we use a string annotation below.
    from chatbot2k.command_handlers.command_handler import CommandHandler


class AppState(ABC):
    @property
    @abstractmethod
    def config(self) -> Config:
        pass

    @property
    @abstractmethod
    def constants(self) -> dict[str, str]:
        pass

    @property
    @abstractmethod
    def command_handlers(self) -> dict[str, "CommandHandler"]:
        pass

    @property
    @abstractmethod
    def broadcasters(self) -> list[Broadcaster]:
        pass

    @property
    @abstractmethod
    def dictionary(self) -> Dictionary:
        pass

    @property
    @abstractmethod
    def translations_manager(self) -> TranslationsManager:
        pass

    @property
    @abstractmethod
    def soundboard_clips_url_queue(self) -> asyncio.Queue:
        pass

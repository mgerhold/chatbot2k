from __future__ import annotations

import asyncio
from abc import ABC
from abc import abstractmethod
from typing import TYPE_CHECKING
from typing import Final
from typing import final
from uuid import UUID

from chatbot2k.broadcasters.broadcaster import Broadcaster
from chatbot2k.config import Config
from chatbot2k.database.engine import Database
from chatbot2k.dictionary import Dictionary
from chatbot2k.translations_manager import TranslationsManager
from chatbot2k.types.commands import Command

if TYPE_CHECKING:
    # We have to avoid circular imports, so we use a string annotation below.
    from chatbot2k.command_handlers.command_handler import CommandHandler
    from chatbot2k.entrance_sounds import EntranceSoundHandler
    from chatbot2k.models.soundboard_event import SoundboardEvent


class AppState(ABC):
    @property
    @abstractmethod
    def config(self) -> Config: ...

    @property
    @abstractmethod
    def database(self) -> Database: ...

    @property
    @abstractmethod
    def command_handlers(self) -> dict[str, CommandHandler]: ...

    @property
    @abstractmethod
    def broadcasters(self) -> list[Broadcaster]: ...

    @property
    @abstractmethod
    def dictionary(self) -> Dictionary: ...

    @property
    @abstractmethod
    def translations_manager(self) -> TranslationsManager: ...

    @property
    @abstractmethod
    def monitored_channels_changed(self) -> asyncio.Event: ...

    @property
    @abstractmethod
    def soundboard_event_queues(self) -> dict[UUID, asyncio.Queue[SoundboardEvent]]: ...

    @final
    async def enqueue_soundboard_clip_url(self, clip_url: str, volume: float) -> None:
        if not self.is_soundboard_enabled:
            return

        # Local import to avoid circular dependency at module level
        from chatbot2k.models.soundboard_event import SoundboardEvent

        event: Final = SoundboardEvent(clip_url=clip_url, volume=volume)
        for queue in self.soundboard_event_queues.values():
            await queue.put(event)

    @property
    @abstractmethod
    def is_soundboard_enabled(self) -> bool: ...

    @is_soundboard_enabled.setter
    @abstractmethod
    def is_soundboard_enabled(self, value: bool) -> None: ...

    @property
    @abstractmethod
    def entrance_sound_handler(self) -> EntranceSoundHandler: ...

    @property
    @abstractmethod
    def command_queue(self) -> asyncio.Queue[Command]:
        """Queue of commands to allow communication between otherwise unrelated components."""

    @abstractmethod
    def reload_command_handlers(self) -> None:
        """Reload all command handlers from the database."""

    @abstractmethod
    async def reload_broadcasters(self) -> None:
        """Reload all broadcasters from the database."""

    @final
    def shut_down(self) -> None:
        self.is_shutting_down.set()

    @property
    @abstractmethod
    def is_shutting_down(self) -> asyncio.Event: ...

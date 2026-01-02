import asyncio
from abc import ABC
from abc import abstractmethod
from typing import TYPE_CHECKING
from typing import Final
from typing import Optional
from uuid import UUID

from chatbot2k.broadcasters.broadcaster import Broadcaster
from chatbot2k.config import Config
from chatbot2k.database.engine import Database
from chatbot2k.dictionary import Dictionary
from chatbot2k.translations_manager import TranslationsManager
from chatbot2k.types.commands import Command
from chatbot2k.types.configuration_setting_kind import ConfigurationSettingKind
from chatbot2k.types.smtp_settings import SmtpCryptoKind
from chatbot2k.types.smtp_settings import SmtpSettings

if TYPE_CHECKING:
    # We have to avoid circular imports, so we use a string annotation below.
    from chatbot2k.command_handlers.command_handler import CommandHandler


class AppState(ABC):
    @property
    @abstractmethod
    def config(self) -> Config: ...

    @property
    @abstractmethod
    def database(self) -> Database: ...

    @property
    @abstractmethod
    def command_handlers(self) -> dict[str, "CommandHandler"]: ...

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
    def soundboard_clips_url_queues(self) -> dict[UUID, asyncio.Queue[str]]: ...

    @property
    @abstractmethod
    def is_soundboard_enabled(self) -> bool: ...

    @is_soundboard_enabled.setter
    @abstractmethod
    def is_soundboard_enabled(self, value: bool) -> None: ...

    @property
    @abstractmethod
    def command_queue(self) -> asyncio.Queue[Command]:
        """Queue of commands to allow communication between otherwise unrelated components."""

    @abstractmethod
    def reload_command_handlers(self) -> None:
        """Reload all command handlers from the database."""

    @property
    def smtp_settings(self) -> Optional[SmtpSettings]:
        host: Final = self.database.retrieve_configuration_setting(ConfigurationSettingKind.SMTP_HOST)
        port: Final = self.database.retrieve_configuration_setting(ConfigurationSettingKind.SMTP_PORT)
        username: Final = self.database.retrieve_configuration_setting(ConfigurationSettingKind.SMTP_USERNAME)
        password: Final = self.database.retrieve_configuration_setting(ConfigurationSettingKind.SMTP_PASSWORD)
        crypto_string: Final = self.database.retrieve_configuration_setting(ConfigurationSettingKind.SMTP_CRYPTO)
        crypto: Final = None if crypto_string is None else SmtpCryptoKind.from_string(crypto_string)
        from_address: Final = self.database.retrieve_configuration_setting(ConfigurationSettingKind.FROM_EMAIL_ADDRESS)
        if (
            host is None
            or not host
            or port is None
            or not port
            or not port.isdigit()
            or username is None
            or not username
            or password is None
            or not password
            or crypto is None
            or from_address is None
            or not from_address
        ):
            return None
        return SmtpSettings(
            host=host,
            port=int(port),
            username=username,
            password=password,
            crypto=crypto,
            from_address=from_address,
        )

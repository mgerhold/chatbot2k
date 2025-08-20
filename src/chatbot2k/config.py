import os
from pathlib import Path
from typing import Final
from typing import NamedTuple
from typing import Optional
from typing import cast
from typing import final
from zoneinfo import ZoneInfo

from dotenv import load_dotenv


def get_environment_variable_or_raise(key: str) -> str:
    value = os.getenv(key)
    if value is None or not value.strip():
        raise ValueError(f"Environment variable '{key}' is not set.")
    return value.strip()


def get_environment_variable_or_default(
    key: str,
    default: str | None,
) -> str | None:
    value = os.getenv(key)
    if value is None or not value.strip():
        return default
    return value.strip()


@final
class OAuthTokens(NamedTuple):
    access_token: str
    refresh_token: str


type TwitchClientSecret = str


@final
class Config:
    _ENV_FILE_PATH = Path(os.getcwd()) / ".env"

    def __init__(self) -> None:
        self._commands_file: Optional[Path] = None
        self._broadcasts_file: Optional[Path] = None
        self._constants_file: Optional[Path] = None
        self._dictionary_file: Optional[Path] = None
        self._translations_file: Optional[Path] = None
        self._timezone: Optional[ZoneInfo] = None
        self._locale: Optional[str] = None
        self._bot_name: Optional[str] = None
        self._author_name: Optional[str] = None
        self._twitch_client_id: Optional[str] = None
        self._twitch_client_secret: Optional[TwitchClientSecret] = None
        self._twitch_credentials: Optional[OAuthTokens] = None
        self._twitch_channel: Optional[str] = None
        self._discord_token: Optional[str] = None
        self.reload()

    def reload(self) -> None:
        load_dotenv()
        self._commands_file = Path(get_environment_variable_or_raise("COMMANDS_FILE"))
        self._broadcasts_file = Path(get_environment_variable_or_raise("BROADCASTS_FILE"))
        self._constants_file = Path(get_environment_variable_or_raise("CONSTANTS_FILE"))
        self._dictionary_file = Path(get_environment_variable_or_raise("DICTIONARY_FILE"))
        self._translations_file = Path(get_environment_variable_or_raise("TRANSLATIONS_FILE"))
        self._timezone = ZoneInfo(get_environment_variable_or_raise("TIMEZONE"))
        self._locale = get_environment_variable_or_raise("LOCALE")
        self._bot_name = get_environment_variable_or_raise("BOT_NAME")
        self._author_name = get_environment_variable_or_raise("AUTHOR_NAME")
        self._twitch_client_id = get_environment_variable_or_raise("TWITCH_CLIENT_ID")
        self._twitch_client_secret = get_environment_variable_or_raise("TWITCH_CLIENT_SECRET")
        twitch_access_token: Final = get_environment_variable_or_default("TWITCH_ACCESS_TOKEN", None)
        twitch_refresh_token: Final = get_environment_variable_or_default("TWITCH_REFRESH_TOKEN", None)
        if twitch_access_token is not None and twitch_refresh_token is not None:
            self._twitch_credentials = OAuthTokens(twitch_access_token, twitch_refresh_token)
        else:
            self._twitch_credentials = None
        self._twitch_channel = get_environment_variable_or_raise("TWITCH_CHANNEL")
        self._discord_token = get_environment_variable_or_raise("DISCORD_BOT_TOKEN")

    @property
    def commands_file(self) -> Path:
        return cast(Path, self._commands_file)

    @property
    def broadcasts_file(self) -> Path:
        return cast(Path, self._broadcasts_file)

    @property
    def constants_file(self) -> Path:
        return cast(Path, self._constants_file)

    @property
    def dictionary_file(self) -> Path:
        return cast(Path, self._dictionary_file)

    @property
    def translations_file(self) -> Path:
        return cast(Path, self._translations_file)

    @property
    def timezone(self) -> ZoneInfo:
        return cast(ZoneInfo, self._timezone)

    @property
    def locale(self) -> str:
        return cast(str, self._locale)

    @property
    def bot_name(self) -> str:
        return cast(str, self._bot_name)

    @property
    def author_name(self) -> str:
        return cast(str, self._author_name)

    @property
    def twitch_client_id(self) -> str:
        return cast(str, self._twitch_client_id)

    @property
    def twitch_client_secret(self) -> TwitchClientSecret:
        return cast(TwitchClientSecret, self._twitch_client_secret)

    @property
    def twitch_credentials(self) -> Optional[OAuthTokens]:
        return cast(Optional[OAuthTokens], self._twitch_credentials)

    @property
    def twitch_channel(self) -> str:
        return cast(str, self._twitch_channel)

    @property
    def discord_token(self) -> str:
        return cast(str, self._discord_token)

    def update_twitch_tokens(self, new_access_token: str, new_refresh_token: str) -> None:
        self._twitch_credentials = OAuthTokens(new_access_token, new_refresh_token)
        # Persist to the `.env` file:
        # - Check whether the entries exist already. If yes, replace them
        # - Otherwise, append them to the end of the file.
        with open(self._ENV_FILE_PATH, "a+") as env_file:
            env_file.seek(0)
            lines = env_file.readlines()
            env_file.seek(0)
            found_access_token = False
            found_refresh_token = False
            for line in lines:
                if line.startswith("TWITCH_ACCESS_TOKEN="):
                    env_file.write(f"TWITCH_ACCESS_TOKEN={new_access_token}\n")
                    found_access_token = True
                elif line.startswith("TWITCH_REFRESH_TOKEN="):
                    env_file.write(f"TWITCH_REFRESH_TOKEN={new_refresh_token}\n")
                    found_refresh_token = True
                else:
                    env_file.write(line)
            if not found_access_token:
                env_file.write(f"TWITCH_ACCESS_TOKEN={new_access_token}\n")
            if not found_refresh_token:
                env_file.write(f"TWITCH_REFRESH_TOKEN={new_refresh_token}\n")

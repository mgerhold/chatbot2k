import os
from pathlib import Path
from typing import Final
from typing import NamedTuple
from typing import final
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()


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
class Config(NamedTuple):
    twitch_client_id: str
    twitch_credentials: TwitchClientSecret | OAuthTokens
    twitch_channel: str
    commands_file: Path
    broadcasts_file: Path
    constants_file: Path
    dictionary_file: Path
    timezone: ZoneInfo
    locale: str


_twitch_client_secret: Final = get_environment_variable_or_default("TWITCH_CLIENT_SECRET", None)
_twitch_access_token: Final = get_environment_variable_or_default("TWITCH_ACCESS_TOKEN", None)
_twitch_refresh_token: Final = get_environment_variable_or_default("TWITCH_REFRESH_TOKEN", None)

if _twitch_access_token is not None and _twitch_refresh_token is not None:
    _twitch_credentials = OAuthTokens(_twitch_access_token, _twitch_refresh_token)
elif _twitch_client_secret is not None:
    _twitch_credentials = _twitch_client_secret
else:
    _twitch_credentials = None

if _twitch_credentials is None:
    raise ValueError("Either TWITCH_CLIENT_SECRET or both TWITCH_ACCESS_TOKEN and TWITCH_REFRESH_TOKEN must be set.")

CONFIG = Config(
    twitch_client_id=get_environment_variable_or_raise("TWITCH_CLIENT_ID"),
    twitch_credentials=_twitch_credentials,
    twitch_channel=get_environment_variable_or_raise("TWITCH_CHANNEL"),
    commands_file=Path(get_environment_variable_or_raise("COMMANDS_FILE")),
    broadcasts_file=Path(get_environment_variable_or_raise("BROADCASTS_FILE")),
    constants_file=Path(get_environment_variable_or_raise("CONSTANTS_FILE")),
    dictionary_file=Path(get_environment_variable_or_raise("DICTIONARY_FILE")),
    timezone=ZoneInfo(get_environment_variable_or_raise("TIMEZONE")),
    locale=get_environment_variable_or_raise("LOCALE"),
)

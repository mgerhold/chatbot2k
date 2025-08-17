import os
from typing import Final
from typing import NamedTuple
from typing import Optional
from typing import final

from dotenv import load_dotenv

load_dotenv()


def get_environment_variable_or_raise(key: str, default: Optional[str] = None) -> str:
    value = os.getenv(key)
    if value is None:
        if default is not None:
            return default
        raise ValueError(f"Environment variable '{key}' is not set.")
    return value


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


_twitch_client_secret: Final = get_environment_variable_or_raise("TWITCH_CLIENT_SECRET", None)
_twitch_access_token: Final = get_environment_variable_or_raise("TWITCH_ACCESS_TOKEN", None)
_twitch_refresh_token: Final = get_environment_variable_or_raise("TWITCH_REFRESH_TOKEN", None)
_twitch_credentials: Final = (
    _twitch_client_secret
    if _twitch_access_token is None and _twitch_refresh_token is None
    else OAuthTokens(_twitch_access_token, _twitch_refresh_token)
)

if _twitch_credentials is None:
    raise ValueError("Either TWITCH_CLIENT_SECRET or both TWITCH_ACCESS_TOKEN and TWITCH_REFRESH_TOKEN must be set.")

CONFIG = Config(
    twitch_client_id=get_environment_variable_or_raise("TWITCH_CLIENT_ID"),
    twitch_credentials=_twitch_credentials,
    twitch_channel=get_environment_variable_or_raise("TWITCH_CHANNEL"),
)

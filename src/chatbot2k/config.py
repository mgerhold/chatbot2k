import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Final
from typing import NamedTuple
from typing import Optional
from typing import final
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

DATABASE_FILE_ENV_VARIABLE = "DATABASE_FILE"

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
class Config:
    _ENV_FILE_PATH = Path(os.getcwd()) / ".env"

    def __init__(self) -> None:
        self._database_file: Optional[Path] = None
        self._timezone: Optional[ZoneInfo] = None
        self._locale: Optional[str] = None
        self._bot_name: Optional[str] = None
        self._author_name: Optional[str] = None
        self._twitch_client_id: Optional[str] = None
        self._twitch_client_secret: Optional[TwitchClientSecret] = None
        self._twitch_credentials: Optional[OAuthTokens] = None
        self._twitch_channel: Optional[str] = None
        self._discord_token: Optional[str] = None
        self._discord_moderator_role_id: Optional[int] = None
        self.reload()

    def reload(self) -> None:
        load_dotenv()
        self._database_file = Path(get_environment_variable_or_raise(DATABASE_FILE_ENV_VARIABLE))
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
        discord_moderator_role_id_str: Final = get_environment_variable_or_default("DISCORD_MODERATOR_ROLE_ID", None)
        if discord_moderator_role_id_str is not None:
            self._discord_moderator_role_id = int(discord_moderator_role_id_str)
        else:
            self._discord_moderator_role_id = None

        self._database_file.parent.mkdir(parents=True, exist_ok=True)

    @property
    def database_file(self) -> Path:
        if self._database_file is None:
            raise AssertionError("Database file path is not set. This should not happen.")
        return self._database_file

    @property
    def timezone(self) -> ZoneInfo:
        if self._timezone is None:
            raise AssertionError("Timezone is not set. This should not happen.")
        return self._timezone

    @property
    def locale(self) -> str:
        if self._locale is None:
            raise AssertionError("Locale is not set. This should not happen.")
        return self._locale

    @property
    def bot_name(self) -> str:
        if self._bot_name is None:
            raise AssertionError("Bot name is not set. This should not happen.")
        return self._bot_name

    @property
    def author_name(self) -> str:
        if self._author_name is None:
            raise AssertionError("Author name is not set. This should not happen.")
        return self._author_name

    @property
    def twitch_client_id(self) -> str:
        if self._twitch_client_id is None:
            raise AssertionError("Twitch client ID is not set. This should not happen.")
        return self._twitch_client_id

    @property
    def twitch_client_secret(self) -> TwitchClientSecret:
        if self._twitch_client_secret is None:
            raise AssertionError("Twitch client secret is not set. This should not happen.")
        return self._twitch_client_secret

    @property
    def twitch_credentials(self) -> Optional[OAuthTokens]:
        return self._twitch_credentials

    @property
    def twitch_channel(self) -> str:
        if self._twitch_channel is None:
            raise AssertionError("Twitch channel is not set. This should not happen.")
        return self._twitch_channel

    @property
    def discord_token(self) -> str:
        if self._discord_token is None:
            raise AssertionError("Discord bot token is not set. This should not happen.")
        return self._discord_token

    @property
    def discord_moderator_role_id(self) -> Optional[int]:
        return self._discord_moderator_role_id

    @staticmethod
    def _update_env_file(path: Path, updates: dict[str, str]) -> None:
        """
        Update or insert KEY=VALUE pairs in a .env file, preserving comments/blank lines.
        - Handles lines like 'KEY=...', '   KEY=...', or 'export KEY=...'
        - Appends missing keys at the end.
        - Atomic write (temp file + os.replace).
        """
        p: Final = Path(path)
        try:
            original = p.read_text(encoding="utf-8")
        except FileNotFoundError:
            original = ""

        lines: Final = original.splitlines(keepends=True)
        found: Final = dict.fromkeys(updates, False)
        new_lines: Final[list[str]] = []

        for line in lines:
            stripped = line.lstrip()
            replaced = False
            for key, value in updates.items():
                # Match 'KEY=' or 'export KEY=' at start of the stripped line.
                if stripped.startswith(f"{key}=") or stripped.startswith(f"export {key}="):
                    leading_ws = line[: len(line) - len(stripped)]
                    export_prefix = "export " if stripped.startswith("export ") else ""
                    newline = "\n" if line.endswith(("\r\n", "\n")) else ""
                    new_lines.append(f"{leading_ws}{export_prefix}{key}={value}{newline}")
                    found[key] = True
                    replaced = True
                    break
            if not replaced:
                new_lines.append(line)

        # Append any keys not found.
        if new_lines and not new_lines[-1].endswith(("\n", "\r\n")):
            new_lines[-1] = new_lines[-1] + "\n"
        for key, value in updates.items():
            if not found[key]:
                new_lines.append(f"{key}={value}\n")

        new_content = "".join(new_lines)

        # Atomic write
        p.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile("w", encoding="utf-8", dir=str(p.parent), delete=False) as tmp:
            tmp.write(new_content)
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp_path = tmp.name
        os.replace(tmp_path, p)

    def update_twitch_tokens(self, new_access_token: str, new_refresh_token: str) -> None:
        self._twitch_credentials = OAuthTokens(new_access_token, new_refresh_token)
        Config._update_env_file(
            self._ENV_FILE_PATH,
            {
                "TWITCH_ACCESS_TOKEN": new_access_token,
                "TWITCH_REFRESH_TOKEN": new_refresh_token,
            },
        )

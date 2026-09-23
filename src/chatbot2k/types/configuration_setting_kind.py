from enum import Enum
from typing import final


@final
class ConfigurationSettingKind(Enum):
    BOT_NAME = "bot_name"
    AUTHOR_NAME = "author_name"
    TIMEZONE = "timezone"
    LOCALE = "locale"
    MAX_PENDING_SOUNDBOARD_CLIPS = "max_pending_soundboard_clips"
    MAX_PENDING_SOUNDBOARD_CLIPS_PER_USER = "max_pending_soundboard_clips_per_user"
    BROADCASTER_EMAIL_ADDRESS = "broadcaster_email_address"
    SCRIPT_EXECUTION_TIMEOUT = "script_execution_timeout"
    DICTIONARY_TWITCH_COOLDOWN_SECONDS = "dictionary_twitch_cooldown_seconds"
    DICTIONARY_DISCORD_COOLDOWN_MESSAGES = "dictionary_discord_cooldown_messages"

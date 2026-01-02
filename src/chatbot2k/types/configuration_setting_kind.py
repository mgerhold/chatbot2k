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

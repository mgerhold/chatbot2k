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
    SMTP_HOST = "smtp_host"
    SMTP_PORT = "smtp_port"
    SMTP_USERNAME = "smtp_username"
    SMTP_PASSWORD = "smtp_password"
    SMTP_CRYPTO = "smtp_crypto"
    FROM_EMAIL_ADDRESS = "from_email_address"

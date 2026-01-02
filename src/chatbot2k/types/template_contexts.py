from enum import StrEnum
from typing import Optional
from typing import final

from pydantic import BaseModel
from pydantic import ConfigDict

from chatbot2k.types.user_info import UserInfo


class CommonContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    bot_name: str
    author_name: str
    copyright_year: int
    current_user: Optional[UserInfo]
    profile_image_url: Optional[str]
    is_broadcaster: bool


@final
class Command(BaseModel):
    model_config = ConfigDict(frozen=True)

    command: str
    description: str
    required_permission_level: str


@final
class DictionaryEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    word: str
    explanation: str


@final
class Constant(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    text: str


@final
class ScriptCommandData(BaseModel):
    model_config = ConfigDict(frozen=True)

    command: str
    source_code: Optional[str]
    source_code_url: Optional[str]


@final
class SoundboardCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    command: str
    clip_url: str


@final
class MainPageContext(CommonContext):
    model_config = ConfigDict(frozen=True)

    commands: list[Command]
    dictionary_entries: list[DictionaryEntry]
    constants: list[Constant]
    script_commands: list[ScriptCommandData]
    soundboard_commands: list[SoundboardCommand]


@final
class ActivePage(StrEnum):
    GENERAL_SETTINGS = "general_settings"
    LIVE_NOTIFICATIONS = "live_notifications"
    SOUNDBOARD = "soundboard"


class DashboardContext(CommonContext):
    model_config = ConfigDict(frozen=True)

    active_page: ActivePage


@final
class DashboardGeneralSettingsContext(DashboardContext):
    model_config = ConfigDict(frozen=True)

    current_bot_name: Optional[str]
    current_author_name: Optional[str]
    current_timezone: Optional[str]
    current_locale: Optional[str]
    available_timezones: list[str]
    available_locales: list[tuple[str, str]]


@final
class LiveNotificationChannel(BaseModel):
    model_config = ConfigDict(frozen=True)

    notification_channel_id: int
    broadcaster_name: str
    broadcaster_id: str
    text_template: str
    target_channel: str


@final
class DashboardLiveNotificationsContext(DashboardContext):
    model_config = ConfigDict(frozen=True)

    channels: list[LiveNotificationChannel]
    discord_text_channels: Optional[list[str]]


@final
class DashboardSoundboardContext(DashboardContext):
    model_config = ConfigDict(frozen=True)

    soundboard_commands: list[SoundboardCommand]

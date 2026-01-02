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
    pending_clips_count: int


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
    uploader_twitch_login: Optional[str]
    uploader_twitch_display_name: Optional[str]


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
    PENDING_CLIPS = "pending_clips"


class AdminContext(CommonContext):
    model_config = ConfigDict(frozen=True)

    active_page: ActivePage


@final
class AdminGeneralSettingsContext(AdminContext):
    model_config = ConfigDict(frozen=True)

    current_bot_name: Optional[str]
    current_author_name: Optional[str]
    current_timezone: Optional[str]
    current_locale: Optional[str]
    current_max_pending_soundboard_clips: Optional[str]
    current_max_pending_soundboard_clips_per_user: Optional[str]
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
class AdminLiveNotificationsContext(AdminContext):
    model_config = ConfigDict(frozen=True)

    channels: list[LiveNotificationChannel]
    discord_text_channels: Optional[list[str]]


@final
class AdminSoundboardContext(AdminContext):
    model_config = ConfigDict(frozen=True)

    soundboard_commands: list[SoundboardCommand]
    existing_commands: list[str]


@final
class PendingClip(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    command: str
    clip_url: str
    may_persist_uploader_info: bool
    uploader_twitch_login: str
    uploader_twitch_display_name: str


@final
class AdminPendingClipsContext(AdminContext):
    model_config = ConfigDict(frozen=True)

    pending_clips: list[PendingClip]
    existing_commands: list[str]


class ViewerContext(CommonContext):
    model_config = ConfigDict(frozen=True)

    active_page: str


@final
class ViewerSoundboardContext(ViewerContext):
    model_config = ConfigDict(frozen=True)

    max_pending_clips: int
    max_pending_clips_per_user: int
    total_pending_clips: int
    user_pending_clips_count: int
    user_can_upload: bool
    pending_clips: list[PendingClip]

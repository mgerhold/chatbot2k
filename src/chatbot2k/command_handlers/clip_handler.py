from typing import Final
from typing import Optional
from typing import final
from typing import override

from chatbot2k.app_state import AppState
from chatbot2k.command_handlers.command_handler import CommandHandler
from chatbot2k.constants import RELATIVE_SOUNDBOARD_FILES_DIRECTORY
from chatbot2k.types.chat_command import ChatCommand
from chatbot2k.types.chat_response import ChatResponse
from chatbot2k.types.permission_level import PermissionLevel


@final
class ClipHandler(CommandHandler):
    def __init__(
        self,
        app_state: AppState,
        *,
        name: str,
        filename: str,
        volume: float,
        uploader_twitch_login: Optional[str] = None,
        uploader_twitch_display_name: Optional[str] = None,
    ) -> None:
        super().__init__(app_state, name=name)
        self._clip_url: Final = f"/{RELATIVE_SOUNDBOARD_FILES_DIRECTORY.as_posix()}/{filename}"
        self._volume: Final = volume
        self._uploader_twitch_login: Final = uploader_twitch_login
        self._uploader_twitch_display_name: Final = uploader_twitch_display_name

    @property
    def clip_url(self) -> str:
        return self._clip_url

    @property
    def uploader_twitch_login(self) -> Optional[str]:
        return self._uploader_twitch_login

    @property
    def uploader_twitch_display_name(self) -> Optional[str]:
        return self._uploader_twitch_display_name

    @property
    def volume(self) -> float:
        return self._volume

    @override
    async def handle_command(self, chat_command: ChatCommand) -> Optional[list[ChatResponse]]:
        if chat_command.source_chat.feature_flags.can_trigger_soundboard:
            await self._app_state.enqueue_soundboard_clip_url(self._clip_url)
        return []

    @property
    @override
    def min_required_permission_level(self) -> PermissionLevel:
        return PermissionLevel.VIEWER

    @property
    @override
    def usage(self) -> str:
        return f"!{self.name}"

    @property
    @override
    def description(self) -> str:
        return f"Plays this clip: {self._clip_url}"

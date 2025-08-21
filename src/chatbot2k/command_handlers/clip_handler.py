from typing import Optional
from typing import final
from typing import override

from chatbot2k.app_state import AppState
from chatbot2k.command_handlers.command_handler import CommandHandler
from chatbot2k.types.chat_command import ChatCommand
from chatbot2k.types.chat_response import ChatResponse
from chatbot2k.types.permission_level import PermissionLevel


@final
class ClipHandler(CommandHandler):
    def __init__(self, app_state: AppState, *, name: str, clip_url: str):
        super().__init__(app_state, name=name)
        self._clip_url = clip_url

    @property
    def clip_url(self) -> str:
        return self._clip_url

    @override
    async def handle_command(self, chat_command: ChatCommand) -> Optional[list[ChatResponse]]:
        if chat_command.source_chat.feature_flags.can_trigger_soundboard:
            await self._app_state.soundboard_clips_url_queue.put(self._clip_url)
        return []

    @override
    @property
    def min_required_permission_level(self) -> PermissionLevel:
        return PermissionLevel.VIEWER

    @override
    @property
    def usage(self) -> str:
        return f"!{self.name}"

    @override
    @property
    def description(self) -> str:
        return f"Plays this clip: {self._clip_url}"

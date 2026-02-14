from __future__ import annotations

import logging
from typing import Final
from typing import Optional
from typing import final

from chatbot2k.app_state import AppState
from chatbot2k.constants import RELATIVE_SOUNDBOARD_FILES_DIRECTORY
from chatbot2k.models.twitch_chat_message_metadata import TwitchChatMessageMetadata
from chatbot2k.types.chat_message import ChatMessage

logger: Final = logging.getLogger(__name__)


@final
class EntranceSoundHandler:
    @final
    class _Passkey: ...

    @final
    class EntranceSoundCommand:
        def __init__(
            self,
            handler: EntranceSoundHandler,
            *,
            sender_twitch_user_id: str,
            clip_url: str,
            _passkey: EntranceSoundHandler._Passkey,
        ) -> None:
            self._handler: Final = handler
            self._sender_twitch_user_id: Final = sender_twitch_user_id
            self._clip_url: Final = clip_url

        async def trigger(self) -> None:
            self._handler._entrance_sounds_already_played_for.add(self._sender_twitch_user_id)
            await self._handler._app_state.enqueue_soundboard_clip_url(self._clip_url, 1.0)

    def __init__(self, app_state: AppState) -> None:
        self._app_state: Final = app_state
        self._entrance_sounds_already_played_for: Final[set[str]] = set()

    async def get_entrance_sound(
        self,
        chat_message: ChatMessage,
    ) -> Optional[EntranceSoundCommand]:
        """
        Triggers entrance sounds for a chat message if applicable. Returns `True`
        if an entrance sound was triggered, otherwise `False`.
        """
        metadata: Final = chat_message.meta_data
        if not isinstance(metadata, TwitchChatMessageMetadata):
            logger.error("Entrance sounds are only supported for Twitch chat messages.")
            return None
        sender_twitch_user_id: Final = metadata.message.user.id
        if sender_twitch_user_id in self._entrance_sounds_already_played_for:
            # This user has already had their entrance sound played during this session.
            return None
        entrance_sound: Final = self._app_state.database.get_entrance_sound_by_twitch_user_id(
            twitch_user_id=sender_twitch_user_id
        )
        if entrance_sound is None:
            return None

        clip_url: Final = f"/{RELATIVE_SOUNDBOARD_FILES_DIRECTORY.as_posix()}/{entrance_sound.filename}"
        return EntranceSoundHandler.EntranceSoundCommand(
            handler=self,
            sender_twitch_user_id=sender_twitch_user_id,
            clip_url=clip_url,
            _passkey=EntranceSoundHandler._Passkey(),
        )

    def reset_entrance_sounds_session(self) -> None:
        """Resets the entrance sounds session, allowing entrance sounds to be played again for all users."""
        self._entrance_sounds_already_played_for.clear()
        logger.info("Entrance sounds session has been reset.")

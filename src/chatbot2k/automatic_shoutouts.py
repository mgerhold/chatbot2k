from __future__ import annotations

import logging
from typing import Final
from typing import Optional
from typing import final

from chatbot2k.app_state import AppState
from chatbot2k.chats.chat import Chat
from chatbot2k.models.twitch_chat_message_metadata import TwitchChatMessageMetadata
from chatbot2k.types.chat_message import ChatMessage
from chatbot2k.types.shoutout_command import ShoutoutCommand
from chatbot2k.utils.twitch import get_twitch_user_by_login

logger: Final = logging.getLogger(__name__)


@final
class AutomaticShoutoutHandler:
    @final
    class _Passkey: ...

    @final
    class AutomaticShoutoutCommand:
        def __init__(
            self,
            handler: AutomaticShoutoutHandler,
            *,
            sender_twitch_user_id: str,
            chat: Chat,
            _passkey: AutomaticShoutoutHandler._Passkey,
        ) -> None:
            self._handler: Final = handler
            self._sender_twitch_user_id: Final = sender_twitch_user_id
            self._chat: Final = chat

        async def trigger(self) -> None:
            self._handler._shoutouts_already_given_to.add(self._sender_twitch_user_id)
            broadcaster: Final = await get_twitch_user_by_login(
                self._handler._app_state.config.twitch_channel, self._handler._app_state
            )
            if broadcaster is None:
                logger.error("Could not resolve the bot's own broadcaster ID, skipping automatic shoutout.")
                return
            await self._chat.shoutout(
                ShoutoutCommand(
                    from_broadcaster_id=broadcaster.id,
                    to_broadcaster_id=self._sender_twitch_user_id,
                )
            )

    def __init__(self, app_state: AppState) -> None:
        self._app_state: Final = app_state
        self._shoutouts_already_given_to: Final[set[str]] = set()

    async def get_shoutout_to_give(
        self,
        chat_message: ChatMessage,
        chat: Chat,
    ) -> Optional[AutomaticShoutoutCommand]:
        """
        Determines whether an automatic shoutout should be given for a chat message.
        Returns an `AutomaticShoutoutCommand` if so, otherwise `None`.
        """
        metadata: Final = chat_message.meta_data
        if not isinstance(metadata, TwitchChatMessageMetadata):
            logger.error("Automatic shoutouts are only supported for Twitch chat messages.")
            return None
        sender_twitch_user_id: Final = metadata.message.user.id
        if sender_twitch_user_id in self._shoutouts_already_given_to:
            # This user has already received an automatic shoutout during this session.
            return None
        automatic_shoutout: Final = self._app_state.database.get_automatic_shoutout_by_twitch_user_id(
            twitch_user_id=sender_twitch_user_id
        )
        if automatic_shoutout is None:
            return None

        return AutomaticShoutoutHandler.AutomaticShoutoutCommand(
            handler=self,
            sender_twitch_user_id=sender_twitch_user_id,
            chat=chat,
            _passkey=AutomaticShoutoutHandler._Passkey(),
        )

    def reset_automatic_shoutouts_session(self) -> None:
        """Resets the automatic shoutouts session, allowing shoutouts to be given again for all users."""
        self._shoutouts_already_given_to.clear()
        logger.info("Automatic shoutouts session has been reset.")

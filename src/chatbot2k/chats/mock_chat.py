import logging
import random
from asyncio import sleep
from collections.abc import AsyncGenerator
from collections.abc import Sequence
from typing import Final
from typing import final
from typing import override

from chatbot2k.chats.chat import Chat
from chatbot2k.types.broadcast_message import BroadcastMessage
from chatbot2k.types.chat_message import ChatMessage
from chatbot2k.types.chat_platform import ChatPlatform
from chatbot2k.types.chat_response import ChatResponse
from chatbot2k.types.live_notification import LiveNotification
from chatbot2k.types.permission_level import PermissionLevel
from chatbot2k.types.shoutout_command import ShoutoutCommand

logger: Final = logging.getLogger(__name__)


@final
class MockChat(Chat):
    @override
    async def get_message_stream(self) -> AsyncGenerator[ChatMessage]:
        for i in range(5):
            await sleep(random.uniform(0.1, 0.5))  # noqa: S311
            yield ChatMessage(
                text=f"Mock message {i + 1}",
                sender_name="mock_user",
                sender_chat=self,
                sender_permission_level=PermissionLevel.VIEWER,
                meta_data=None,
            )

    @override
    async def send_responses(self, responses: Sequence[ChatResponse]) -> None:
        for response in responses:
            logger.info(f"Mock response sent: {response.text}")

    @override
    async def send_broadcast(self, message: BroadcastMessage) -> None:
        logger.info(f"Mock broadcast sent: {message.text}")

    @override
    async def post_live_notification(self, notification: LiveNotification) -> None:
        logger.info(f"Mock live notification posted: {notification.render_text()}")

    @override
    async def react_to_raid(self, message: BroadcastMessage) -> None:
        logger.info(f"Mock raid reaction sent: {message.text}")

    @override
    async def shoutout(self, command: ShoutoutCommand) -> None:
        logger.info(f"Mock shoutout sent: {command}")

    @property
    @override
    def platform(self) -> ChatPlatform:
        return ChatPlatform.MOCK

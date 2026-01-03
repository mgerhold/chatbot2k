from collections.abc import Awaitable
from collections.abc import Callable
from typing import Final
from typing import final

from chatbot2k.chats.discord_chat import DiscordChat


@final
class RetrieveDiscordChatCommand:
    def __init__(self, callback: Callable[[DiscordChat], Awaitable[None]]) -> None:
        self._callback: Final = callback

    async def execute(self, discord_chat: DiscordChat) -> None:
        await self._callback(discord_chat)


@final
class ReloadBroadcastersCommand: ...


type Command = RetrieveDiscordChatCommand | ReloadBroadcastersCommand

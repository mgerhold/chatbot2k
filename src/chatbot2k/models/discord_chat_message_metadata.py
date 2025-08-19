from typing import NamedTuple
from typing import final

from discord import Message


@final
class DiscordChatMessageMetadata(NamedTuple):
    message: Message

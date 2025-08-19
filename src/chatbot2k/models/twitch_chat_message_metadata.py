from typing import NamedTuple
from typing import final

from twitchAPI.chat import ChatMessage


@final
class TwitchChatMessageMetadata(NamedTuple):
    message: ChatMessage

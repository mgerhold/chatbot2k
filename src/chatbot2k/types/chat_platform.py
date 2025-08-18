from enum import Enum
from enum import auto
from typing import final


@final
class ChatPlatform(Enum):
    TWITCH = auto()
    DISCORD = auto()
    MOCK = auto()

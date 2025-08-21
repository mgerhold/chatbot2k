from typing import NamedTuple
from typing import final


@final
class ChatFeatures(NamedTuple):
    regular_chat: bool  # Can this chat be used for regular conversations?
    broadcasting: bool  # Is this chat capable of broadcasting messages?

from typing import NamedTuple
from typing import final


@final
class ChatFeatures(NamedTuple):
    REGULAR_CHAT: bool  # Can this chat be used for regular conversations?
    BROADCASTING: bool  # Is this chat capable of broadcasting messages?

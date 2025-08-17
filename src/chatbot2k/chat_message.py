from typing import NamedTuple
from typing import final


@final
class ChatMessage(NamedTuple):
    text: str

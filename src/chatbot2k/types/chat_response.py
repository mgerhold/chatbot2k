from typing import NamedTuple
from typing import final


@final
class ChatResponse(NamedTuple):
    text: str

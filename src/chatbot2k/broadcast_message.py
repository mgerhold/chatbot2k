from typing import NamedTuple
from typing import final


@final
class BroadcastMessage(NamedTuple):
    text: str

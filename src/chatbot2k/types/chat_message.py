from typing import Any
from typing import NamedTuple
from typing import final


@final
class ChatMessage(NamedTuple):
    text: str
    sender_name: str
    meta_data: Any  # Platform-specific metadata.

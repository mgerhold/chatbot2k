from typing import Any
from typing import NamedTuple
from typing import final

from chatbot2k.types.permission_level import PermissionLevel


@final
class ChatMessage(NamedTuple):
    text: str
    sender_name: str
    sender_permission_level: PermissionLevel
    meta_data: Any  # Platform-specific metadata.

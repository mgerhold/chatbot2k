from typing import TYPE_CHECKING
from typing import Any
from typing import NamedTuple
from typing import final

from chatbot2k.types.permission_level import PermissionLevel

if TYPE_CHECKING:
    from chatbot2k.chats.chat import Chat


@final
class ChatMessage(NamedTuple):
    text: str
    sender_name: str
    sender_chat: "Chat"
    sender_permission_level: PermissionLevel
    meta_data: Any  # Platform-specific metadata.

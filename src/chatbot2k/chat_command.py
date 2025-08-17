from typing import Final
from typing import NamedTuple
from typing import Optional
from typing import final

from chatbot2k.chat_message import ChatMessage


@final
class ChatCommand(NamedTuple):
    name: str
    arguments: list[str]


def to_chat_command(message: ChatMessage) -> Optional[ChatCommand]:
    text: Final = message.text.strip()
    if not text.startswith("!"):
        return None
    parts: list[str] = text.split()
    name: Final = parts.pop(0).removeprefix("!").strip()
    if not name:
        return None
    stripped_parts: Final = [part.strip() for part in parts if part.strip()]
    arguments: Final = [part for part in stripped_parts if part]  # Remove empty strings.
    return ChatCommand(name=name, arguments=arguments)

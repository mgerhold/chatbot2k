from typing import Final
from typing import NamedTuple
from typing import Optional
from typing import Self
from typing import final

from chatbot2k.types.chat_message import ChatMessage


@final
class ChatCommand(NamedTuple):
    name: str
    arguments: list[str]
    source_message: ChatMessage

    @classmethod
    def from_chat_message(cls, message: ChatMessage) -> Optional[Self]:
        text: Final = message.text.strip()
        if not text.startswith("!"):
            return None
        parts: list[str] = text.split()
        name: Final = parts.pop(0).removeprefix("!").strip()
        if not name:
            return None
        stripped_parts: Final = [part.strip() for part in parts if part.strip()]
        arguments: Final = [part for part in stripped_parts if part]  # Remove empty strings.
        return cls(
            name=name,
            arguments=arguments,
            source_message=message,
        )

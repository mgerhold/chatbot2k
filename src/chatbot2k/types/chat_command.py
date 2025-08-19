import shlex
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

        # Use shlex to respect quotes and escapes; disable comment parsing.
        lexer = shlex.shlex(text, posix=True)
        lexer.whitespace_split = True
        lexer.commenters = ""  # treat '#' as normal char, not a comment

        try:
            parts = list(lexer)
        except ValueError:
            # Unbalanced quotes -> not a valid command
            return None

        if not parts:
            return None

        # First token is the command; strip the leading '!'
        name = parts.pop(0).removeprefix("!").strip()
        if not name:
            return None

        arguments: Final = parts  # already quote-aware tokens
        return cls(name=name, arguments=arguments, source_message=message)

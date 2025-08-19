from typing import NamedTuple
from typing import final

from chatbot2k.types.chat_message import ChatMessage


@final
class ChatResponse(NamedTuple):
    text: str
    chat_message: ChatMessage  # The chat message that triggered this response.

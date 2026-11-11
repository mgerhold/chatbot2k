from pathlib import Path
from typing import NamedTuple
from typing import Optional
from typing import final

from chatbot2k.types.chat_message import ChatMessage


@final
class ChatAttachment(NamedTuple):
    """A media file that accompanies a response (e.g. a soundboard clip)."""

    path: Path  # Local path of the file, to be uploaded if the chat supports it.
    url: str  # Publicly reachable URL of the same file, used if uploading is not possible.


@final
class ChatResponse(NamedTuple):
    text: str
    chat_message: ChatMessage  # The chat message that triggered this response.
    attachment: Optional[ChatAttachment]  # Media file to post along with (or instead of) the text, if any.

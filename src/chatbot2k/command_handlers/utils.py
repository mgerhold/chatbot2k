from chatbot2k.builtins import apply_builtins
from chatbot2k.config import Config
from chatbot2k.constants import replace_constants
from chatbot2k.database.tables import Constant
from chatbot2k.types.chat_message import ChatMessage


def replace_placeholders_in_message(
    *,
    text: str,
    source_message: ChatMessage,
    constants: list[Constant],
    config: Config,
) -> str:
    text = text.replace("{SENDER_NAME}", source_message.sender_name)
    text = apply_builtins(text, config)  # `{CURRENT_DATE}`, etc.
    text = replace_constants(text, constants)  # User-defined global constants.
    return text

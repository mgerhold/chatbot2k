from chatbot2k.builtins import apply_builtins
from chatbot2k.constants import replace_constants
from chatbot2k.types.chat_message import ChatMessage


def replace_placeholders_in_message(text: str, source_message: ChatMessage) -> str:
    text = text.replace("{SENDER_NAME}", source_message.sender_name)
    text = apply_builtins(text)  # `{CURRENT_DATE}`, etc.
    text = replace_constants(text)  # User-defined global constants.
    return text

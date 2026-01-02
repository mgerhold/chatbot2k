from chatbot2k.app_state import AppState
from chatbot2k.broadcasters.utils import replace_constants
from chatbot2k.builtins import apply_builtins
from chatbot2k.database.tables import Constant
from chatbot2k.types.chat_message import ChatMessage


def replace_placeholders_in_message(
    *,
    text: str,
    source_message: ChatMessage,
    constants: list[Constant],
    app_state: AppState,
) -> str:
    text = text.replace("{SENDER_NAME}", source_message.sender_name)
    text = apply_builtins(text, app_state)  # `{CURRENT_DATE}`, etc.
    text = replace_constants(text, constants)  # User-defined global constants.
    return text
